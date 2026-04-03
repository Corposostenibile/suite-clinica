"""
monitoring/service_v2.py
========================
Servizio per interrogare i log del GCP HTTP Load Balancer
tramite Cloud Logging API (non più gcloud CLI).

Logica:
- Usa google-cloud-logging API con paginazione
- Fetch parallelo per giorno (un thread per giorno)
- Parsa i risultati JSON
- Aggrega per endpoint, fascia oraria, giorno della settimana
- Distingue chiamate "esterne" (dal LB verso il backend) e chiamate
  "verso servizi esterni" (GHL, Gemini, SMTP - queste richiedono log applicativi)

Miglioramenti rispetto alla versione 1:
- Cloud Logging API nativa (più veloce e affidabile)
- Nessun limite di campionamento (recupera tutti i dati)
- Caching Redis per ridurre chiamate API
- Kubernetes API nativa per metriche infrastrutturali
"""
from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

# Google Cloud Libraries
from google.cloud.logging_v2.services.logging_service_v2 import LoggingServiceV2Client
from google.cloud.logging_v2.types import ListLogEntriesRequest
from google.cloud import monitoring_v3
from google.cloud import container_v1
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import DefaultCredentialsError

# Kubernetes Python client
from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException

# Redis caching
from corposostenibile.extensions import get_redis_client, is_redis_available, get_cache_key


# ── Logging helper ──────────────────────────────────────────────────────────

import logging as _logging

_logger = _logging.getLogger(__name__)


def _log_info(msg: str, *args) -> None:
    try:
        current_app.logger.info(msg, *args)
    except RuntimeError:
        _logger.info(msg, *args)


def _log_error(msg: str, *args) -> None:
    try:
        current_app.logger.error(msg, *args)
    except RuntimeError:
        _logger.error(msg, *args)


# ── Pattern per normalizzare le URL ─────────────────────────────────────────

# Lista di pattern da normalizzare: (regex, sostituzione)
_URL_NORMALIZERS: List[Tuple[re.Pattern, str]] = [
    # UUID e token lunghi
    (re.compile(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'), '/{uuid}'),
    # Token alfanumerici lunghi (>20 chars)
    (re.compile(r'/[A-Za-z0-9_-]{20,}'), '/{token}'),
    # ID numerici
    (re.compile(r'/\d+'), '/{id}'),
    # Nomi di file con estensione (preserva l'estensione)
    (re.compile(r'/[^/]+\.(jpg|jpeg|png|gif|webp|pdf|css|js|woff2?|ttf|svg|ico|map)$', re.I), '/*.\x01'),
]

# Prefissi da escludere (file statici / asset)
_STATIC_PREFIXES = (
    '/static/',
    '/uploads/',
    '/assets/',
    '/favicon',
    '/manifest',
    '/sw.js',
    '/workbox-',
    '/push-sw.js',
)

# ── Classificazione endpoint ────────────────────────────────────────────────

# Endpoint che fanno chiamate a servizi esterni (GHL, Gemini AI, SMTP)
_EXTERNAL_CALL_PATTERNS = [
    '/ghl/',
    '/api/team/assignments/analyze-lead',
    '/api/client-checks/public/weekly/',  # invia notifiche push/email
]

# Patterns piu' specifici: (url_contains, method) -> external
_EXTERNAL_CALL_EXACT = [
    ('/nutrition/add', 'POST'),           # nutrition/add invia email
]


def _normalize_url(raw_url: str) -> str:
    """Normalizza una URL rimuovendo host, query string e parametri dinamici."""
    # Rimuovi schema + host
    if '://' in raw_url:
        raw_url = raw_url.split('/', 3)[-1]
        if not raw_url.startswith('/'):
            raw_url = '/' + raw_url

    # Rimuovi query string
    url = raw_url.split('?')[0]

    # Applica normalizzatori (tranne file extension, gestito separatamente)
    for pattern, replacement in _URL_NORMALIZERS[:-1]:
        url = pattern.sub(replacement, url)

    # File extension: preserva estensione reale
    file_pattern = _URL_NORMALIZERS[-1][0]
    m = file_pattern.search(url)
    if m:
        ext = m.group(1).lower()
        url = file_pattern.sub(f'/*.{ext}', url)

    return url


def _is_static(url: str) -> bool:
    """True se l'URL e' un asset statico (non un endpoint API)."""
    return any(url.startswith(p) for p in _STATIC_PREFIXES)


def _classify_endpoint(normalized_url: str, method: str = 'GET') -> str:
    """
    Classifica un endpoint:
    - 'external_call': il backend fa chiamate verso servizi esterni
    - 'internal': endpoint che lavora solo con DB/Redis locali
    - 'static': file statico
    """
    if _is_static(normalized_url):
        return 'static'
    for pattern in _EXTERNAL_CALL_PATTERNS:
        if pattern in normalized_url:
            return 'external_call'
    for url_part, req_method in _EXTERNAL_CALL_EXACT:
        if url_part in normalized_url and method.upper() == req_method:
            return 'external_call'
    return 'internal'


def _parse_latency(latency_str: str) -> float:
    """Parsa '0.123456s' -> 0.123456"""
    if not latency_str:
        return 0.0
    try:
        return float(latency_str.rstrip('s'))
    except (ValueError, AttributeError):
        return 0.0


# ══════════════════════════════════════════════════════════════════════════════
#                    CLOUD LOGGING API (nuova implementazione)
# ══════════════════════════════════════════════════════════════════════════════

def _get_logging_client() -> LoggingServiceV2Client:
    """Ottiene il client Cloud Logging."""
    return LoggingServiceV2Client()


def _fetch_logs_for_day_api(
    date: datetime,
    per_day_limit: Optional[int] = 10000,  # None o 0 significa "tutti i dati"
    timeout_s: int = 60,
) -> tuple[str, List[Dict[str, Any]]]:
    """
    Scarica i log di UN singolo giorno (UTC) usando Cloud Logging API.
    Ritorna (date_str, entries).
    
    Miglioramenti:
    - Nessun subprocess
    - Gestione errori API nativa
    - Timeout configurable
    """
    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end   = day_start + timedelta(days=1)
    date_str  = day_start.strftime('%Y-%m-%d')
    start_str = day_start.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_str   = day_end.strftime('%Y-%m-%dT%H:%M:%SZ')

    filter_str = (
        f'resource.type="http_load_balancer" '
        f'timestamp>="{start_str}" timestamp<"{end_str}" '
        f'httpRequest.requestUrl=~"/(api|old-suite|ghl|check|postit|clienti)/" '
    )
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = _get_logging_client()
            entries = []
            
            # Determina page_size e se applicare limite
            if per_day_limit is None or per_day_limit == 0:
                page_size = 1000  # Massimo per pagina, nessun limite totale
                limit = None
            else:
                page_size = min(per_day_limit, 1000)
                limit = per_day_limit
            
            # Costruisci la request con page_size
            request = ListLogEntriesRequest(
                resource_names=["projects/suite-clinica"],
                filter=filter_str,
                page_size=page_size,
            )
            
            # Cloud Logging API con paginazione
            response = client.list_log_entries(
                request=request,
                timeout=timeout_s,
            )
            
            # Itera attraverso le entry (il pager è iterable)
            for entry in response:
                # Converti entry protobuf in dict
                entry_dict = _protobuf_entry_to_dict(entry)
                entries.append(entry_dict)
                
                # Stop se raggiungiamo il limite (se applicabile)
                if limit is not None and len(entries) >= limit:
                    break
            
            _log_info("[monitoring] day=%s → %d entries (API)", date_str, len(entries))
            return date_str, entries
            
        except GoogleAPIError as e:
            # Se è un errore 429 (rate limit) e abbiamo tentativi, aspetta con backoff
            if hasattr(e, 'code') and e.code == 429 and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1, 2, 4 secondi
                _log_info("[monitoring] Rate limit hit for day=%s, retrying in %ds (attempt %d/%d)", 
                         date_str, wait_time, attempt + 1, max_retries)
                time.sleep(wait_time)
                continue
            _log_error("[monitoring] Cloud Logging API error day=%s: %s", date_str, str(e))
            return date_str, []
        except DefaultCredentialsError as e:
            _log_error("[monitoring] GCP credentials not found: %s", str(e))
            return date_str, []
        except Exception as e:
            _log_error("[monitoring] Unexpected error day=%s: %s", date_str, str(e))
            return date_str, []
    # Should not reach here, but just in case
    return date_str, []


def _protobuf_entry_to_dict(entry) -> Dict[str, Any]:
    """Converte un entry protobuf Cloud Logging in dict."""
    entry_dict = {}
    
    # Timestamp
    if entry.timestamp:
        entry_dict['timestamp'] = entry.timestamp.isoformat()
    
    # HTTP Request
    if entry.http_request:
        http_req = {}
        if entry.http_request.request_url:
            http_req['requestUrl'] = entry.http_request.request_url
        if entry.http_request.request_method:
            http_req['requestMethod'] = entry.http_request.request_method
        if entry.http_request.status:
            http_req['status'] = entry.http_request.status
        if entry.http_request.latency:
            latency = entry.http_request.latency
            total_seconds = latency.seconds + latency.nanos / 1e9
            http_req['latency'] = f"{total_seconds}s"
        entry_dict['httpRequest'] = http_req
    
    # Labels (per eventuali dati aggiuntivi)
    if entry.labels:
        entry_dict['labels'] = dict(entry.labels)
    
    return entry_dict


def _fetch_logs_api(
    days: int = 7,
    per_day_limit: Optional[int] = 10000,  # None o 0 significa "tutti i dati"
    use_cache: bool = True,
    cache_ttl: int = 300,  # 5 minuti di cache
) -> List[Dict[str, Any]]:
    """
    Scarica i log degli ultimi N giorni con fetch parallelo usando Cloud Logging API.
    
    Args:
        days: Numero di giorni da recuperare
        per_day_limit: Limite per giorno (None o 0 = tutti i dati)
        use_cache: Se usare la cache Redis
        cache_ttl: Tempo di vita della cache in secondi
    """
    now = datetime.now(timezone.utc)
    dates = [now - timedelta(days=i) for i in range(days)]

    limit_for_cache = per_day_limit if per_day_limit is not None else 0
    _log_info("[monitoring] Fetching logs via API: days=%d, per_day_limit=%s", days, per_day_limit)

    # Controlla cache Redis
    if use_cache and is_redis_available():
        redis_client = get_redis_client()
        cache_key = get_cache_key("monitoring:logs", days, limit_for_cache)
        
        cached_data = redis_client.get(cache_key)
        if cached_data:
            _log_info("[monitoring] Cache hit for logs: %s", cache_key)
            return json.loads(cached_data)

    # Fetch sequenziale per evitare rate limit (max 60 richieste/min)
    all_entries: List[Dict[str, Any]] = []
    
    for i, d in enumerate(dates):
        if i > 0:
            time.sleep(1)  # Pausa di 1 secondo tra richieste per sicurezza
        date_str, entries = _fetch_logs_for_day_api(d, per_day_limit)
        all_entries.extend(entries)

    # Salva in cache
    if use_cache and is_redis_available() and all_entries:
        redis_client = get_redis_client()
        cache_key = get_cache_key("monitoring:logs", days, limit_for_cache)
        redis_client.setex(cache_key, cache_ttl, json.dumps(all_entries))
        _log_info("[monitoring] Saved logs to cache: %s", cache_key)

    return all_entries


# ══════════════════════════════════════════════════════════════════════════════
#                    PARSING E AGGREGAZIONE (invariata)
# ══════════════════════════════════════════════════════════════════════════════

def _parse_entries(raw_entries: List[Dict]) -> List[Dict[str, Any]]:
    """Trasforma i log grezzi in record strutturati."""
    records = []
    for entry in raw_entries:
        http_req = entry.get('httpRequest', {})
        raw_url = http_req.get('requestUrl', '')
        if not raw_url:
            continue

        normalized = _normalize_url(raw_url)
        method = http_req.get('requestMethod', 'GET')
        classification = _classify_endpoint(normalized, method)

        ts_str = entry.get('timestamp', '')
        try:
            # Supporta sia formato ISO che timestamp numerico
            if isinstance(ts_str, (int, float)):
                ts = datetime.fromtimestamp(ts_str, tz=timezone.utc)
            else:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError, TypeError):
            continue

        records.append({
            'url': normalized,
            'method': method,
            'status': http_req.get('status', 0),
            'latency': _parse_latency(http_req.get('latency', '0s')),
            'timestamp': ts,
            'hour': ts.hour,
            'weekday': ts.weekday(),  # 0=Mon, 6=Sun
            'date_str': ts.strftime('%Y-%m-%d'),
            'classification': classification,
        })

    return records


# ── Aggregazioni ────────────────────────────────────────────────────────────

_WEEKDAY_NAMES = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']


def _aggregate_metrics(
    records: List[Dict],
    include_static: bool = False,
) -> Dict[str, Any]:
    """
    Calcola tutte le metriche richieste:
    1. Chiamate medie al giorno per API
    2. Tempo medio per chiamata API
    3. Distribuzione oraria per API
    4. Distribuzione per giorno della settimana per API
    5. Errori (status >= 400)
    """
    if not records:
        return {
            'endpoints': [],
            'errors': [],
            'period_days': 0,
            'total_requests': 0,
        }

    # Filtra statici se non richiesti
    if not include_static:
        records = [r for r in records if r['classification'] != 'static']

    if not records:
        return {
            'endpoints': [],
            'errors': [],
            'period_days': 0,
            'total_requests': 0,
        }

    # Calcola periodo coperto
    dates = {r['date_str'] for r in records}
    num_days = max(len(dates), 1)

    # Raggruppa per (method, url, classification)
    by_endpoint: Dict[str, List[Dict]] = defaultdict(list)
    errors: List[Dict] = []

    for r in records:
        key = f"{r['method']} {r['url']}"
        by_endpoint[key].append(r)
        if r['status'] >= 400:
            errors.append(r)

    # Costruisci metriche per endpoint
    endpoints = []
    for endpoint_key, reqs in by_endpoint.items():
        method, url = endpoint_key.split(' ', 1)
        classification = reqs[0]['classification']
        latencies = [r['latency'] for r in reqs]
        total_count = len(reqs)

        # Distribuzione oraria (0-23)
        hourly = defaultdict(int)
        for r in reqs:
            hourly[r['hour']] += 1
        hourly_dist = [
            {'hour': h, 'count': hourly.get(h, 0)}
            for h in range(24)
        ]

        # Distribuzione per giorno settimana
        weekday = defaultdict(int)
        for r in reqs:
            weekday[r['weekday']] += 1
        # Normalizza per numero di occorrenze del giorno nel periodo
        weekday_dates: Dict[int, set] = defaultdict(set)
        for r in reqs:
            weekday_dates[r['weekday']].add(r['date_str'])

        weekday_dist = []
        for wd in range(7):
            count = weekday.get(wd, 0)
            days_with_data = max(len(weekday_dates.get(wd, set())), 1)
            weekday_dist.append({
                'day': _WEEKDAY_NAMES[wd],
                'day_index': wd,
                'total': count,
                'avg_per_day': round(count / days_with_data, 1),
            })

        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
        max_latency = max(latencies) if latencies else 0

        endpoints.append({
            'method': method,
            'url': url,
            'classification': classification,
            'total_requests': total_count,
            'avg_per_day': round(total_count / num_days, 1),
            'avg_latency_ms': round(avg_latency * 1000),
            'p95_latency_ms': round(p95_latency * 1000),
            'max_latency_ms': round(max_latency * 1000),
            'error_count': sum(1 for r in reqs if r['status'] >= 400),
            'error_rate_pct': round(
                sum(1 for r in reqs if r['status'] >= 400) / total_count * 100, 1
            ),
            'hourly_distribution': hourly_dist,
            'weekday_distribution': weekday_dist,
        })

    # Ordina per avg_per_day descending
    endpoints.sort(key=lambda e: e['avg_per_day'], reverse=True)

    # Errori: raggruppa per endpoint + status
    error_summary = defaultdict(lambda: {'count': 0, 'last_seen': '', 'samples': []})
    for e in errors:
        key = f"{e['method']} {e['url']} [{e['status']}]"
        error_summary[key]['count'] += 1
        ts_str = e['timestamp'].isoformat()
        if ts_str > error_summary[key]['last_seen']:
            error_summary[key]['last_seen'] = ts_str
        if len(error_summary[key]['samples']) < 3:
            error_summary[key]['samples'].append({
                'timestamp': ts_str,
                'status': e['status'],
                'latency_ms': round(e['latency'] * 1000),
            })

    error_list = [
        {
            'endpoint': k.rsplit(' [', 1)[0],
            'status': int(k.rsplit('[', 1)[1].rstrip(']')),
            'count': v['count'],
            'last_seen': v['last_seen'],
            'samples': v['samples'],
        }
        for k, v in error_summary.items()
    ]
    error_list.sort(key=lambda e: e['count'], reverse=True)

    return {
        'endpoints': endpoints,
        'errors': error_list,
        'period_days': num_days,
        'total_requests': len(records),
    }


# ══════════════════════════════════════════════════════════════════════════════
#                       METRICHE INFRASTRUTTURALI (API native)
# ══════════════════════════════════════════════════════════════════════════════

def _get_kubernetes_client() -> Optional[client.CoreV1Api]:
    """Ottiene il client Kubernetes configurato."""
    try:
        # Prova a caricare la configurazione in-cluster (GKE)
        try:
            config.load_incluster_config()
        except ConfigException:
            # Fallback: carica da kubeconfig (sviluppo locale)
            config.load_kube_config()
        
        return client.CoreV1Api()
    except Exception as e:
        _log_error("[monitoring] Kubernetes client error: %s", str(e))
        return None


def _get_apps_client() -> Optional[client.AppsV1Api]:
    """Ottiene il client AppsV1 (per deployment)."""
    try:
        try:
            config.load_incluster_config()
        except ConfigException:
            config.load_kube_config()
        
        return client.AppsV1Api()
    except Exception as e:
        _log_error("[monitoring] Kubernetes apps client error: %s", str(e))
        return None


def _get_autoscaling_client() -> Optional[client.AutoscalingV1Api]:
    """Ottiene il client AutoscalingV1 (per HPA)."""
    try:
        try:
            config.load_incluster_config()
        except ConfigException:
            config.load_kube_config()
        
        return client.AutoscalingV1Api()
    except Exception as e:
        _log_error("[monitoring] Kubernetes autoscaling client error: %s", str(e))
        return None


def get_pod_metrics() -> List[Dict[str, Any]]:
    """
    Metriche dei pod usando Kubernetes Metrics API.
    Nota: richiede metrics-server installato nel cluster.
    """
    try:
        # Usa il custom metrics API o metrics-server
        api = _get_kubernetes_client()
        if not api:
            return []
        
        # Recupera le metriche dai pod
        # Nota: il Metrics API è separato dal Core API
        # Per semplicità, usiamo le label dei pod per calcolare utilizzo
        pods = api.list_namespaced_pod(
            namespace="default",
            label_selector="app=suite-clinica-backend"
        )
        
        pod_metrics = []
        for pod in pods.items:
            pod_name = pod.metadata.name
            
            # Per metriche reali, serve metrics-server e k8s API separata
            # Qui restituiamo info base del pod
            pod_metrics.append({
                'name': pod_name,
                'cpu_millicores': None,  # Richiede metrics-server
                'memory_mib': None,      # Richiede metrics-server
                'status': pod.status.phase,
                'node': pod.spec.node_name or '',
                'ip': pod.status.pod_ip or '',
            })
        
        return pod_metrics
        
    except Exception as e:
        _log_error("[monitoring] Pod metrics error: %s", str(e))
        return []


def get_node_metrics() -> List[Dict[str, Any]]:
    """Metriche dei nodi usando Kubernetes Metrics API."""
    try:
        api = _get_kubernetes_client()
        if not api:
            return []
        
        nodes = api.list_node()
        
        node_metrics = []
        for node in nodes.items:
            node_name = node.metadata.name
            
            # Estrai capacity dal node
            capacity = node.status.capacity or {}
            allocatable = node.status.allocatable or {}
            
            cpu_capacity = capacity.get('cpu', '0')
            memory_capacity = capacity.get('memory', '0')
            
            # Converti in formato leggibile
            cpu_millicores = _parse_cpu_k8s(cpu_capacity)
            memory_mib = _parse_memory_k8s(memory_capacity)
            
            node_metrics.append({
                'name': node_name,
                'cpu_millicores': cpu_millicores,
                'cpu_pct': None,  # Richiede metrics-server per utilizzo effettivo
                'memory_mib': memory_mib,
                'memory_pct': None,  # Richiede metrics-server per utilizzo effettivo
            })
        
        return node_metrics
        
    except Exception as e:
        _log_error("[monitoring] Node metrics error: %s", str(e))
        return []


def _parse_cpu_k8s(cpu_str: str) -> Optional[int]:
    """Parsa CPU Kubernetes (es. '1000m' -> 1000, '1' -> 1000)."""
    if not cpu_str:
        return None
    try:
        if cpu_str.endswith('m'):
            return int(cpu_str[:-1])
        return int(float(cpu_str) * 1000)
    except (ValueError, AttributeError):
        return None


def _parse_memory_k8s(memory_str: str) -> Optional[int]:
    """Parsa memoria Kubernetes (es. '1Gi' -> 1024, '512Mi' -> 512)."""
    if not memory_str:
        return None
    try:
        if memory_str.endswith('Ki'):
            return int(float(memory_str[:-2]) / 1024)
        if memory_str.endswith('Mi'):
            return int(memory_str[:-2])
        if memory_str.endswith('Gi'):
            return int(float(memory_str[:-2]) * 1024)
        if memory_str.endswith('Ti'):
            return int(float(memory_str[:-3]) * 1024 * 1024)
        # Fallback: assume bytes
        return int(float(memory_str) / (1024 * 1024))
    except (ValueError, AttributeError):
        return None


def get_hpa_status() -> List[Dict[str, Any]]:
    """Stato degli HPA usando Kubernetes API."""
    try:
        api = _get_autoscaling_client()
        if not api:
            return []
        
        hpa_list = api.list_horizontal_pod_autoscaler_for_all_namespaces()
        
        hpas = []
        for hpa in hpa_list.items:
            spec = hpa.spec
            status = hpa.status
            
            # Estrai metriche target e correnti
            current_metrics = {}
            target_metrics = {}
            
            if status.current_metrics:
                for metric in status.current_metrics:
                    if metric.resource:
                        res_name = metric.resource.name
                        if metric.resource.current:
                            current_metrics[res_name] = (
                                metric.resource.current.average_utilization
                            )
            
            if spec.metrics:
                for metric in spec.metrics:
                    if metric.resource:
                        res_name = metric.resource.name
                        if metric.resource.target:
                            target_metrics[res_name] = (
                                metric.resource.target.average_utilization
                            )
            
            hpas.append({
                'name': hpa.metadata.name,
                'reference': spec.scale_target_ref.name,
                'min_replicas': spec.min_replicas or 0,
                'max_replicas': spec.max_replicas or 0,
                'current_replicas': status.current_replicas or 0,
                'desired_replicas': status.desired_replicas or 0,
                'cpu_current_pct': current_metrics.get('cpu'),
                'cpu_target_pct': target_metrics.get('cpu'),
                'memory_current_pct': current_metrics.get('memory'),
                'memory_target_pct': target_metrics.get('memory'),
            })
        
        return hpas
        
    except Exception as e:
        _log_error("[monitoring] HPA status error: %s", str(e))
        return []


def get_deployment_info() -> Dict[str, Any]:
    """Info sul deployment backend usando Kubernetes API."""
    try:
        api = _get_apps_client()
        if not api:
            return {}
        
        deployment = api.read_namespaced_deployment(
            name="suite-clinica-backend",
            namespace="default"
        )
        
        spec = deployment.spec
        container = spec.template.spec.containers[0] if spec.template.spec.containers else None
        resources = container.resources if container else None
        
        return {
            'replicas': spec.replicas or 0,
            'strategy': spec.strategy.type if spec.strategy else 'Unknown',
            'image': container.image if container else '',
            'command': ' '.join(container.command or []) if container else '',
            'requests_cpu': resources.requests.cpu if resources and resources.requests else '',
            'requests_memory': resources.requests.memory if resources and resources.requests else '',
            'limits_cpu': resources.limits.cpu if resources and resources.limits else '',
            'limits_memory': resources.limits.memory if resources and resources.limits else '',
            'ready_replicas': deployment.status.ready_replicas or 0,
            'available_replicas': deployment.status.available_replicas or 0,
        }
        
    except Exception as e:
        _log_error("[monitoring] Deployment info error: %s", str(e))
        return {}


def get_pods_status() -> List[Dict[str, Any]]:
    """Stato dei pod usando Kubernetes API."""
    try:
        api = _get_kubernetes_client()
        if not api:
            return []
        
        pods = api.list_namespaced_pod(
            namespace="default",
            label_selector="app=suite-clinica-backend"
        )
        
        pod_list = []
        for pod in pods.items:
            containers = pod.status.container_statuses or []
            restart_count = sum(c.restart_count or 0 for c in containers)
            ready_count = sum(1 for c in containers if c.ready)
            total_count = len(containers)
            
            pod_list.append({
                'name': pod.metadata.name,
                'status': pod.status.phase,
                'ready': f'{ready_count}/{total_count}',
                'restarts': restart_count,
                'node': pod.spec.node_name or '',
                'age': pod.metadata.creation_timestamp.isoformat() if pod.metadata.creation_timestamp else '',
                'ip': pod.status.pod_ip or '',
            })
        
        return pod_list
        
    except Exception as e:
        _log_error("[monitoring] Pods status error: %s", str(e))
        return []


def get_cloud_sql_info() -> Dict[str, Any]:
    """Info Cloud SQL usando Google Cloud SQL Admin API."""
    try:
        from googleapiclient.discovery import build
        
        service = build('sqladmin', 'v1beta4')
        
        # Recupera info sull'istanza
        instance = service.instances().get(
            project='suite-clinica',
            instance='suite-clinica-db-prod'
        ).execute()
        
        settings = instance.get('settings', {})
        
        return {
            'tier': settings.get('tier', ''),
            'disk_size_gb': settings.get('dataDiskSizeGb', ''),
            'disk_type': settings.get('dataDiskType', ''),
            'database_version': instance.get('databaseVersion', ''),
            'state': instance.get('state', ''),
            'region': instance.get('region', ''),
            'availability_type': settings.get('availabilityType', ''),
        }
        
    except Exception as e:
        _log_error("[monitoring] Cloud SQL info error: %s", str(e))
        return {}


def get_infrastructure_data(use_cache: bool = True, cache_ttl: int = 60) -> Dict[str, Any]:
    """
    Raccoglie tutte le metriche infrastrutturali in un'unica chiamata.
    Usa cache Redis per ridurre chiamate API.
    
    Args:
        use_cache: Se usare la cache Redis
        cache_ttl: Tempo di vita della cache in secondi (default 60s)
    """
    # Controlla cache Redis
    if use_cache and is_redis_available():
        redis_client = get_redis_client()
        cache_key = get_cache_key("monitoring:infrastructure")
        
        cached_data = redis_client.get(cache_key)
        if cached_data:
            _log_info("[monitoring] Cache hit for infrastructure: %s", cache_key)
            return json.loads(cached_data)
    
    # Recupera dati freschi
    data = {
        'pods_metrics': get_pod_metrics(),
        'nodes_metrics': get_node_metrics(),
        'hpa': get_hpa_status(),
        'deployment': get_deployment_info(),
        'pods_status': get_pods_status(),
        'cloud_sql': get_cloud_sql_info(),
    }
    
    # Salva in cache
    if use_cache and is_redis_available():
        redis_client = get_redis_client()
        cache_key = get_cache_key("monitoring:infrastructure")
        redis_client.setex(cache_key, cache_ttl, json.dumps(data))
        _log_info("[monitoring] Saved infrastructure to cache: %s", cache_key)
    
    return data


# ══════════════════════════════════════════════════════════════════════════════
#                       API PUBBLICA DEL SERVIZIO
# ══════════════════════════════════════════════════════════════════════════════

def get_monitoring_data(
    days: int = 7,
    include_static: bool = False,
    per_day_limit: Optional[int] = 10000,  # None o 0 significa "tutti i dati"
    use_cache: bool = True,
    cache_ttl: int = 300,  # 5 minuti
) -> Dict[str, Any]:
    """
    Scarica tutti i giorni in parallelo, aggrega e ritorna.
    Usa Cloud Logging API nativa + caching Redis.
    
    Args:
        days: Numero di giorni da analizzare
        include_static: Se includere endpoint statici
        per_day_limit: Limite entry per giorno (None o 0 = tutti i dati)
        use_cache: Se usare la cache Redis
        cache_ttl: Tempo di vita della cache in secondi
    """
    raw = _fetch_logs_api(
        days=days,
        per_day_limit=per_day_limit,
        use_cache=use_cache,
        cache_ttl=cache_ttl
    )
    records = _parse_entries(raw)
    metrics = _aggregate_metrics(records, include_static=include_static)
    metrics['fetched_entries'] = len(raw)
    metrics['parsed_records'] = len(records)
    return metrics