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
    per_day_limit: Optional[int] = 500,
    timeout_s: int = 30,
) -> tuple[str, List[Dict[str, Any]]]:
    """
    Scarica i log di UN singolo giorno (UTC) usando Cloud Logging API.
    
    Strategia: divide il giorno in 4 fasce di 6 ore e distribuisce
    il budget equamente, così il campione copre tutto il giorno
    e tutti gli endpoint (anche quelli usati solo in certi orari).
    """
    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    date_str  = day_start.strftime('%Y-%m-%d')
    
    limit = per_day_limit if per_day_limit and per_day_limit > 0 else 500
    
    # Dividi in 4 fasce da 6 ore con budget equo
    NUM_SLICES = 4
    HOURS_PER_SLICE = 6
    per_slice_limit = max(50, limit // NUM_SLICES)
    
    all_entries: List[Dict[str, Any]] = []
    
    for s in range(NUM_SLICES):
        slice_start = day_start + timedelta(hours=s * HOURS_PER_SLICE)
        slice_end   = slice_start + timedelta(hours=HOURS_PER_SLICE)
        start_str = slice_start.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_str   = slice_end.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        filter_str = (
            f'resource.type="http_load_balancer" '
            f'timestamp>="{start_str}" timestamp<"{end_str}" '
            f'httpRequest.requestUrl=~"/(api|old-suite|ghl|check|postit|clienti)/" '
        )
        
        try:
            client = _get_logging_client()
            page_size = min(per_slice_limit, 1000)
            
            request = ListLogEntriesRequest(
                resource_names=["projects/suite-clinica"],
                filter=filter_str,
                page_size=page_size,
            )
            
            response = client.list_log_entries(
                request=request,
                timeout=timeout_s,
            )
            
            count = 0
            for page in response.pages:
                for entry in page.entries:
                    all_entries.append(_protobuf_entry_to_dict(entry))
                    count += 1
                    if count >= per_slice_limit:
                        break
                if count >= per_slice_limit:
                    break
                    
        except GoogleAPIError as e:
            _log_error("[monitoring] Logging API error day=%s slice=%d: %s", date_str, s, str(e))
        except DefaultCredentialsError as e:
            _log_error("[monitoring] GCP credentials not found: %s", str(e))
            return date_str, []
        except Exception as e:
            _log_error("[monitoring] Unexpected error day=%s slice=%d: %s", date_str, s, str(e))
    
    _log_info("[monitoring] day=%s → %d entries (4 slices)", date_str, len(all_entries))
    return date_str, all_entries


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
    per_day_limit: Optional[int] = 500,
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

    all_entries: List[Dict[str, Any]] = []
    
    # Eseguiamo in parallelo con ThreadPoolExecutor (max 4 thread)
    with ThreadPoolExecutor(max_workers=min(days, 4)) as executor:
        futures = {executor.submit(_fetch_logs_for_day_api, d, per_day_limit): d for d in dates}
        for future in as_completed(futures):
            try:
                date_str, entries = future.result()
                all_entries.extend(entries)
            except Exception as e:
                _log_error("[monitoring] Error fetching logs in thread: %s", str(e))

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
            label_selector="app=suite-clinica-backend",
            _request_timeout=15
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
        
        nodes = api.list_node(_request_timeout=15)
        
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
    """Stato degli HPA usando Kubernetes AutoscalingV1 API."""
    try:
        api = _get_autoscaling_client()
        if not api:
            return []
        
        hpa_list = api.list_horizontal_pod_autoscaler_for_all_namespaces(_request_timeout=15)
        
        hpas = []
        for hpa in hpa_list.items:
            spec = hpa.spec
            status = hpa.status
            
            # V1 HPA: solo CPU target/current
            cpu_target = spec.target_cpu_utilization_percentage
            cpu_current = status.current_cpu_utilization_percentage
            
            hpas.append({
                'name': hpa.metadata.name,
                'reference': spec.scale_target_ref.name,
                'min_replicas': spec.min_replicas or 0,
                'max_replicas': spec.max_replicas or 0,
                'current_replicas': status.current_replicas or 0,
                'desired_replicas': status.desired_replicas or 0,
                'cpu_current_pct': cpu_current,
                'cpu_target_pct': cpu_target,
                'memory_current_pct': None,
                'memory_target_pct': None,
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
            namespace="default",
            _request_timeout=15
        )
        
        spec = deployment.spec
        container = spec.template.spec.containers[0] if spec.template.spec.containers else None
        resources = container.resources if container else None
        
        return {
            'replicas': spec.replicas or 0,
            'strategy': spec.strategy.type if spec.strategy else 'Unknown',
            'image': container.image if container else '',
            'command': ' '.join(container.command or []) if container else '',
            'requests_cpu': (resources.requests or {}).get('cpu', '') if resources else '',
            'requests_memory': (resources.requests or {}).get('memory', '') if resources else '',
            'limits_cpu': (resources.limits or {}).get('cpu', '') if resources else '',
            'limits_memory': (resources.limits or {}).get('memory', '') if resources else '',
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
            label_selector="app=suite-clinica-backend",
            _request_timeout=15
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
    
    # Recupera dati freschi in parallelo
    with ThreadPoolExecutor(max_workers=6) as executor:
        f_pods = executor.submit(get_pod_metrics)
        f_nodes = executor.submit(get_node_metrics)
        f_hpa = executor.submit(get_hpa_status)
        f_deploy = executor.submit(get_deployment_info)
        f_status = executor.submit(get_pods_status)
        f_sql = executor.submit(get_cloud_sql_info)
    
    data = {
        'pods_metrics': f_pods.result(),
        'nodes_metrics': f_nodes.result(),
        'hpa': f_hpa.result(),
        'deployment': f_deploy.result(),
        'pods_status': f_status.result(),
        'cloud_sql': f_sql.result(),
    }
    
    # Salva in cache
    if use_cache and is_redis_available():
        redis_client = get_redis_client()
        cache_key = get_cache_key("monitoring:infrastructure")
        redis_client.setex(cache_key, cache_ttl, json.dumps(data))
        _log_info("[monitoring] Saved infrastructure to cache: %s", cache_key)
    
    return data


# ══════════════════════════════════════════════════════════════════════════════
#              CLOUD MONITORING API (metriche pre-aggregate GCP)
# ══════════════════════════════════════════════════════════════════════════════

_GCP_PROJECT = "projects/suite-clinica"

# Metriche LB disponibili:
# - loadbalancing.googleapis.com/https/request_count  (DELTA, INT64)
# - loadbalancing.googleapis.com/https/total_latencies (DELTA, DISTRIBUTION)
# - loadbalancing.googleapis.com/https/backend_latencies (DELTA, DISTRIBUTION)


def _get_monitoring_client() -> monitoring_v3.MetricServiceClient:
    """Ottiene il client Cloud Monitoring."""
    return monitoring_v3.MetricServiceClient()


def _build_time_interval(days: int) -> monitoring_v3.TimeInterval:
    """Costruisce l'intervallo temporale per le query."""
    from google.protobuf.timestamp_pb2 import Timestamp as PbTimestamp
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    interval = monitoring_v3.TimeInterval()
    interval.end_time = PbTimestamp(seconds=int(now.timestamp()))
    interval.start_time = PbTimestamp(seconds=int(start.timestamp()))
    return interval


def _fetch_request_counts(
    client: monitoring_v3.MetricServiceClient,
    days: int,
) -> Dict[str, Any]:
    """
    Recupera conteggio richieste dal LB, raggruppato per response_code_class.
    Filtra solo il backend target dell'app (esclude health check, bot, static).
    """
    interval = _build_time_interval(days)

    # Filtra solo il path rule "/" (il nostro backend reale).
    # Esclude UNMATCHED (bot/scanner) e UNKNOWN (traffico non classificato).
    metric_filter = (
        'metric.type = "loadbalancing.googleapis.com/https/request_count" '
        'resource.type = "https_lb_rule" '
        'resource.label.matched_url_path_rule = "/"'
    )

    request_obj = monitoring_v3.ListTimeSeriesRequest(
        name=_GCP_PROJECT,
        filter=metric_filter,
        interval=interval,
        view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        aggregation=monitoring_v3.Aggregation(
            alignment_period={"seconds": 3600},  # 1 ora
            per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_SUM,
            cross_series_reducer=monitoring_v3.Aggregation.Reducer.REDUCE_SUM,
            group_by_fields=["metric.label.response_code_class"],
        ),
    )

    total_requests = 0
    errors_4xx = 0
    errors_5xx = 0
    hourly_counts = defaultdict(int)
    weekday_counts = defaultdict(int)
    daily_counts = defaultdict(int)

    try:
        results = client.list_time_series(request=request_obj, timeout=15)
        for ts in results:
            code_class = ts.metric.labels.get("response_code_class", "")
            _log_info("[monitoring] request_count: response_code_class=%s", code_class)
            for point in ts.points:
                count = point.value.int64_value
                total_requests += count

                pt_time = point.interval.start_time
                pt_dt = datetime.fromtimestamp(pt_time.timestamp(), tz=timezone.utc)
                hourly_counts[pt_dt.hour] += count
                weekday_counts[pt_dt.weekday()] += count
                daily_counts[pt_dt.strftime('%Y-%m-%d')] += count

                # response_code_class è un intero come 200, 300, 400, 500
                if str(code_class) == "400":
                    errors_4xx += count
                elif str(code_class) == "500":
                    errors_5xx += count
    except Exception as e:
        _log_error("[monitoring] Cloud Monitoring request_count error: %s", str(e))

    num_days = max(len(daily_counts), 1)

    hourly_distribution = [
        {"hour": h, "count": hourly_counts.get(h, 0)}
        for h in range(24)
    ]

    weekday_names = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']
    weekday_distribution = [
        {
            "day": weekday_names[wd],
            "day_index": wd,
            "total": weekday_counts.get(wd, 0),
            "avg_per_day": round(weekday_counts.get(wd, 0) / max(1, sum(
                1 for d in daily_counts if datetime.strptime(d, '%Y-%m-%d').weekday() == wd
            )), 1),
        }
        for wd in range(7)
    ]

    return {
        "total_requests": total_requests,
        "avg_requests_per_day": round(total_requests / num_days, 1),
        "errors_4xx": errors_4xx,
        "errors_5xx": errors_5xx,
        "error_rate_pct": round((errors_4xx + errors_5xx) / max(total_requests, 1) * 100, 1),
        "period_days": num_days,
        "hourly_distribution": hourly_distribution,
        "weekday_distribution": weekday_distribution,
    }


def _fetch_latency_stats(
    client: monitoring_v3.MetricServiceClient,
    days: int,
) -> Dict[str, Any]:
    """
    Recupera statistiche latenza dal LB usando la metrica distribution.
    
    NOTA: loadbalancing.googleapis.com/https/total_latencies è in MILLISECONDI.
    I valori mean, bucket bounds e range sono già in ms, NON moltiplicare x1000.
    """
    interval = _build_time_interval(days)

    # Filtra solo path rule "/" (esclude bot/scanner che generano UNMATCHED)
    metric_filter = (
        'metric.type = "loadbalancing.googleapis.com/https/total_latencies" '
        'resource.type = "https_lb_rule" '
        'resource.label.matched_url_path_rule = "/"'
    )

    request_obj = monitoring_v3.ListTimeSeriesRequest(
        name=_GCP_PROJECT,
        filter=metric_filter,
        interval=interval,
        view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        aggregation=monitoring_v3.Aggregation(
            alignment_period={"seconds": days * 86400},
            per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_DELTA,
            cross_series_reducer=monitoring_v3.Aggregation.Reducer.REDUCE_SUM,
        ),
    )

    total_count = 0
    weighted_sum = 0.0
    max_latency = 0.0
    # Accumula tutti i bucket per calcolo percentili
    merged_bucket_counts: List[int] = []
    bucket_bounds: List[float] = []

    try:
        results = client.list_time_series(request=request_obj, timeout=15)
        for ts in results:
            for point in ts.points:
                dist = point.value.distribution_value
                if dist.count == 0:
                    continue

                total_count += dist.count
                # dist.mean è già in ms
                weighted_sum += dist.mean * dist.count

                # Estrai bucket bounds (una sola volta, sono uguali per tutte le serie)
                if not bucket_bounds:
                    if dist.bucket_options.explicit_buckets.bounds:
                        bucket_bounds = list(dist.bucket_options.explicit_buckets.bounds)
                    elif dist.bucket_options.exponential_buckets.num_finite_buckets > 0:
                        eb = dist.bucket_options.exponential_buckets
                        bucket_bounds = [
                            eb.scale * (eb.growth_factor ** i)
                            for i in range(eb.num_finite_buckets + 1)
                        ]
                    _log_info("[monitoring] Latency bucket_bounds (%d): first=%s, last=%s",
                              len(bucket_bounds),
                              bucket_bounds[:3] if bucket_bounds else 'none',
                              bucket_bounds[-3:] if bucket_bounds else 'none')

                # Somma bucket counts (per merge di più serie)
                counts = list(dist.bucket_counts)
                if not merged_bucket_counts:
                    merged_bucket_counts = counts
                else:
                    for j in range(min(len(counts), len(merged_bucket_counts))):
                        merged_bucket_counts[j] += counts[j]
                    # Se la nuova serie ha più bucket
                    if len(counts) > len(merged_bucket_counts):
                        merged_bucket_counts.extend(counts[len(merged_bucket_counts):])

                # dist.range non è popolato per aggregazioni, calcoleremo il max dai bucket
                pass

        _log_info("[monitoring] Latency raw: total_count=%d, weighted_sum=%.1f, "
                  "mean=%.1fms, max=%.1fms, buckets=%d, bounds=%d",
                  total_count, weighted_sum,
                  weighted_sum / max(total_count, 1), max_latency,
                  len(merged_bucket_counts), len(bucket_bounds))

    except Exception as e:
        _log_error("[monitoring] Cloud Monitoring latency error: %s", str(e))

    # Media (già in ms)
    avg_ms = round(weighted_sum / max(total_count, 1))

    # Calcola percentili dai bucket
    # Per exponential buckets: bound[i] = scale * growth_factor^i
    # bucket_counts[0] = underflow (< bound[0])
    # bucket_counts[i] per i>=1 = count con bound[i-1] <= x < bound[i]
    # L'ultimo bucket_counts è overflow (>= ultimo bound)
    p50_ms = 0
    p95_ms = 0
    p99_ms = 0
    max_latency_ms = 0

    if merged_bucket_counts and bucket_bounds:
        cumulative = 0
        for i, bc in enumerate(merged_bucket_counts):
            cumulative += bc
            pct = cumulative / max(total_count, 1)

            # Il bound superiore di questo bucket
            if i == 0:
                upper_bound = bucket_bounds[0] if bucket_bounds else 0
            elif i <= len(bucket_bounds):
                upper_bound = bucket_bounds[i - 1]
            else:
                upper_bound = bucket_bounds[-1] if bucket_bounds else 0

            # Traccia l'ultimo bucket con dati per stimare il max
            if bc > 0:
                max_latency_ms = round(upper_bound)

            if p50_ms == 0 and pct >= 0.50:
                p50_ms = round(upper_bound)
            if p95_ms == 0 and pct >= 0.95:
                p95_ms = round(upper_bound)
            if p99_ms == 0 and pct >= 0.99:
                p99_ms = round(upper_bound)
                break

    _log_info("[monitoring] Latency results: avg=%dms, p50=%dms, p95=%dms, p99=%dms, max=%dms",
              avg_ms, p50_ms, p95_ms, p99_ms, round(max_latency))

    return {
        "avg_latency_ms": avg_ms,
        "p50_latency_ms": p50_ms,
        "p95_latency_ms": p95_ms,
        "p99_latency_ms": p99_ms,
        "max_latency_ms": max_latency_ms,
        "sample_count": total_count,
    }


def get_overview_data(
    days: int = 7,
    use_cache: bool = True,
    cache_ttl: int = 300,
) -> Dict[str, Any]:
    """
    Overview della dashboard usando Cloud Monitoring API (metriche pre-aggregate).
    Istantaneo (~1-2 secondi), nessun log grezzo da scaricare.

    Dati forniti:
    - Totale richieste e media/giorno
    - Errori 4xx/5xx e percentuale
    - Latenza media, p50, p95, p99, max
    - Distribuzione oraria (tutte le request)
    - Distribuzione settimanale (tutte le request)
    """
    # Controlla cache
    if use_cache and is_redis_available():
        redis_client = get_redis_client()
        cache_key = get_cache_key("monitoring:overview", days)
        cached = redis_client.get(cache_key)
        if cached:
            _log_info("[monitoring] Cache hit for overview: %s", cache_key)
            return json.loads(cached)

    try:
        client = _get_monitoring_client()

        # Fetch parallelo: conteggi e latenze
        with ThreadPoolExecutor(max_workers=2) as executor:
            f_counts = executor.submit(_fetch_request_counts, client, days)
            f_latency = executor.submit(_fetch_latency_stats, client, days)

        counts = f_counts.result()
        latency = f_latency.result()

        data = {
            "source": "cloud_monitoring",
            "period_days": counts["period_days"],
            **counts,
            **latency,
        }

    except (GoogleAPIError, DefaultCredentialsError) as e:
        _log_error("[monitoring] Cloud Monitoring overview error: %s", str(e))
        data = {
            "source": "cloud_monitoring",
            "error": str(e),
            "total_requests": 0,
            "period_days": 0,
        }

    # Salva in cache
    if use_cache and is_redis_available() and data.get("total_requests", 0) > 0:
        redis_client = get_redis_client()
        cache_key = get_cache_key("monitoring:overview", days)
        redis_client.setex(cache_key, cache_ttl, json.dumps(data))
        _log_info("[monitoring] Saved overview to cache: %s", cache_key)

    return data


# ══════════════════════════════════════════════════════════════════════════════
#                       API PUBBLICA DEL SERVIZIO
# ══════════════════════════════════════════════════════════════════════════════

def get_monitoring_data(
    days: int = 7,
    include_static: bool = False,
    per_day_limit: Optional[int] = 500,
    use_cache: bool = True,
    cache_ttl: int = 300,  # 5 minuti
) -> Dict[str, Any]:
    """
    Dettaglio per endpoint: scarica log e aggrega.
    Usato solo per il tab "Dettaglio API" (non per overview).
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