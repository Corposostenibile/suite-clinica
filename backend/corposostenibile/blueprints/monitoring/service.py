"""
monitoring/service.py
=====================
Servizio per interrogare i log del GCP HTTP Load Balancer
tramite gcloud CLI (gia' autenticato sul VPS).

Logica:
- Usa `gcloud logging read` con filtri per resource.type="http_load_balancer"
- Parsa i risultati JSON
- Aggrega per endpoint, fascia oraria, giorno della settimana
- Distingue chiamate "esterne" (dal LB verso il backend) e chiamate
  "verso servizi esterni" (GHL, Gemini, SMTP - queste richiedono log applicativi)
"""
from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from functools import lru_cache

from flask import current_app


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
    return float(latency_str.rstrip('s'))


# ── Query Cloud Logging ─────────────────────────────────────────────────────

def _fetch_logs_for_day(date: datetime, per_day_limit: int, timeout_s: int = 20) -> List[Dict[str, Any]]:
    """
    Scarica i log di UN singolo giorno (UTC).
    Ritorna lista vuota in caso di errore.
    """
    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end   = day_start + timedelta(days=1)
    start_str = day_start.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_str   = day_end.strftime('%Y-%m-%dT%H:%M:%SZ')

    filter_str = (
        f'resource.type="http_load_balancer" '
        f'timestamp>="{start_str}" timestamp<"{end_str}"'
    )
    cmd = [
        'gcloud', 'logging', 'read', filter_str,
        '--project=suite-clinica',
        f'--limit={per_day_limit}',
        '--format=json',
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        if result.returncode != 0:
            _log_error("[monitoring] gcloud error day=%s: %s", start_str[:10], result.stderr[:200])
            return []
        return json.loads(result.stdout) if result.stdout.strip() else []
    except subprocess.TimeoutExpired:
        _log_error("[monitoring] gcloud timeout day=%s", start_str[:10])
        return []
    except json.JSONDecodeError as e:
        _log_error("[monitoring] JSON parse error day=%s: %s", start_str[:10], e)
        return []


def _fetch_logs(days: int = 7, per_day_limit: int = 300) -> List[Dict[str, Any]]:
    """
    Scarica i log degli ultimi N giorni con fetch parallelo (un thread per giorno).
    Ogni giorno viene campionato con al massimo `per_day_limit` entry.

    Tempo atteso: ~8-12s indipendentemente dal numero di giorni (bounded dal thread più lento).
    """
    now = datetime.now(timezone.utc)
    dates = [now - timedelta(days=i) for i in range(days)]

    _log_info("[monitoring] Fetching logs: days=%d, per_day_limit=%d (parallel)", days, per_day_limit)

    all_entries: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(days, 7)) as executor:
        futures = {
            executor.submit(_fetch_logs_for_day, d, per_day_limit): d
            for d in dates
        }
        for future in as_completed(futures):
            try:
                entries = future.result()
                all_entries.extend(entries)
                _log_info("[monitoring] day=%s → %d entries", futures[future].strftime('%Y-%m-%d'), len(entries))
            except Exception as e:
                _log_error("[monitoring] future error: %s", e)

    return all_entries


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
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
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


# ── API pubblica del servizio ───────────────────────────────────────────────

def get_monitoring_data(
    days: int = 7,
    include_static: bool = False,
    per_day_limit: int = 300,
) -> Dict[str, Any]:
    """
    Entry-point principale: scarica log (campionati per giorno), parsa, aggrega.
    Ritorna il dizionario completo con tutte le metriche.
    """
    raw = _fetch_logs(days=days, per_day_limit=per_day_limit)
    records = _parse_entries(raw)
    metrics = _aggregate_metrics(records, include_static=include_static)
    metrics['fetched_entries'] = len(raw)
    metrics['parsed_records'] = len(records)
    metrics['per_day_limit'] = per_day_limit
    return metrics


# ══════════════════════════════════════════════════════════════════════════════
#                       METRICHE INFRASTRUTTURALI (kubectl + gcloud)
# ══════════════════════════════════════════════════════════════════════════════

def _run_cmd(cmd: List[str], timeout_s: int = 15) -> Optional[str]:
    """Esegue un comando e ritorna stdout, o None in caso di errore."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        if result.returncode != 0:
            _log_error("[monitoring] cmd error %s: %s", cmd[0], result.stderr[:200])
            return None
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        _log_error("[monitoring] cmd timeout: %s", ' '.join(cmd[:3]))
        return None
    except FileNotFoundError:
        _log_error("[monitoring] cmd not found: %s", cmd[0])
        return None


def _parse_cpu(val: str) -> Optional[int]:
    """Parsa '555m' -> 555 (millicores), '2' -> 2000."""
    if not val:
        return None
    val = val.strip()
    if val.endswith('m'):
        return int(val[:-1])
    try:
        return int(float(val) * 1000)
    except ValueError:
        return None


def _parse_memory(val: str) -> Optional[int]:
    """Parsa '1284Mi' -> 1284 (MiB), '4Gi' -> 4096, '1G' -> ~953."""
    if not val:
        return None
    val = val.strip()
    if val.endswith('Mi'):
        return int(val[:-2])
    if val.endswith('Gi'):
        return int(float(val[:-2]) * 1024)
    if val.endswith('Ki'):
        return int(float(val[:-2]) / 1024)
    if val.endswith('M'):
        return int(float(val[:-1]) * 1000000 / (1024 * 1024))
    if val.endswith('G'):
        return int(float(val[:-1]) * 1000000000 / (1024 * 1024))
    try:
        return int(float(val) / (1024 * 1024))
    except ValueError:
        return None


def get_pod_metrics() -> List[Dict[str, Any]]:
    """kubectl top pods: ritorna CPU e memoria per pod."""
    output = _run_cmd(['kubectl', 'top', 'pods', '--no-headers'])
    if not output:
        return []

    pods = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        pods.append({
            'name': parts[0],
            'cpu_millicores': _parse_cpu(parts[1]),
            'memory_mib': _parse_memory(parts[2]),
        })
    return pods


def get_node_metrics() -> List[Dict[str, Any]]:
    """kubectl top nodes: ritorna CPU e memoria per nodo."""
    output = _run_cmd(['kubectl', 'top', 'nodes', '--no-headers'])
    if not output:
        return []

    nodes = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        nodes.append({
            'name': parts[0],
            'cpu_millicores': _parse_cpu(parts[1]),
            'cpu_pct': parts[2].rstrip('%'),
            'memory_mib': _parse_memory(parts[3]),
            'memory_pct': parts[4].rstrip('%'),
        })
    return nodes


def get_hpa_status() -> List[Dict[str, Any]]:
    """kubectl get hpa: ritorna stato HPA."""
    output = _run_cmd(['kubectl', 'get', 'hpa', '-o', 'json'])
    if not output:
        return []

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []

    hpas = []
    for item in data.get('items', []):
        spec = item.get('spec', {})
        status = item.get('status', {})
        metrics_status = status.get('currentMetrics', [])

        current_metrics = {}
        for m in metrics_status:
            res_name = m.get('resource', {}).get('name', '')
            current_val = m.get('resource', {}).get('current', {})
            if res_name:
                current_metrics[res_name] = current_val.get('averageUtilization')

        target_metrics = {}
        for m in spec.get('metrics', []):
            res_name = m.get('resource', {}).get('name', '')
            target_val = m.get('resource', {}).get('target', {})
            if res_name:
                target_metrics[res_name] = target_val.get('averageUtilization')

        hpas.append({
            'name': item['metadata']['name'],
            'reference': spec.get('scaleTargetRef', {}).get('name', ''),
            'min_replicas': spec.get('minReplicas', 0),
            'max_replicas': spec.get('maxReplicas', 0),
            'current_replicas': status.get('currentReplicas', 0),
            'desired_replicas': status.get('desiredReplicas', 0),
            'cpu_current_pct': current_metrics.get('cpu'),
            'cpu_target_pct': target_metrics.get('cpu'),
            'memory_current_pct': current_metrics.get('memory'),
            'memory_target_pct': target_metrics.get('memory'),
        })
    return hpas


def get_deployment_info() -> Dict[str, Any]:
    """kubectl get deployment: info sul deployment backend."""
    output = _run_cmd(['kubectl', 'get', 'deployment', 'suite-clinica-backend', '-o', 'json'])
    if not output:
        return {}

    try:
        d = json.loads(output)
    except json.JSONDecodeError:
        return {}

    spec = d.get('spec', {})
    container = spec.get('template', {}).get('spec', {}).get('containers', [{}])[0]
    resources = container.get('resources', {})

    return {
        'replicas': spec.get('replicas', 0),
        'strategy': spec.get('strategy', {}).get('type', 'Unknown'),
        'image': container.get('image', ''),
        'command': ' '.join(container.get('command', [])),
        'requests_cpu': resources.get('requests', {}).get('cpu', ''),
        'requests_memory': resources.get('requests', {}).get('memory', ''),
        'limits_cpu': resources.get('limits', {}).get('cpu', ''),
        'limits_memory': resources.get('limits', {}).get('memory', ''),
        'ready_replicas': d.get('status', {}).get('readyReplicas', 0),
        'available_replicas': d.get('status', {}).get('availableReplicas', 0),
    }


def get_pods_status() -> List[Dict[str, Any]]:
    """kubectl get pods: stato dei pod."""
    output = _run_cmd(['kubectl', 'get', 'pods', '-o', 'json'])
    if not output:
        return []

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return []

    pods = []
    for item in data.get('items', []):
        meta = item.get('metadata', {})
        status = item.get('status', {})
        containers = status.get('containerStatuses', [])

        restart_count = sum(c.get('restartCount', 0) for c in containers)
        ready_count = sum(1 for c in containers if c.get('ready', False))
        total_count = len(containers)

        pods.append({
            'name': meta.get('name', ''),
            'status': status.get('phase', 'Unknown'),
            'ready': f'{ready_count}/{total_count}',
            'restarts': restart_count,
            'node': spec.get('nodeName', '') if (spec := item.get('spec', {})) else '',
            'age': meta.get('creationTimestamp', ''),
            'ip': status.get('podIP', ''),
        })
    return pods


def get_cloud_sql_info() -> Dict[str, Any]:
    """gcloud sql instances describe: info Cloud SQL."""
    output = _run_cmd([
        'gcloud', 'sql', 'instances', 'describe', 'suite-clinica-db-prod',
        '--format=json',
    ], timeout_s=20)
    if not output:
        return {}

    try:
        d = json.loads(output)
    except json.JSONDecodeError:
        return {}

    settings = d.get('settings', {})
    return {
        'tier': settings.get('tier', ''),
        'disk_size_gb': settings.get('dataDiskSizeGb', ''),
        'disk_type': settings.get('dataDiskType', ''),
        'database_version': d.get('databaseVersion', ''),
        'state': d.get('state', ''),
        'region': d.get('region', ''),
        'availability_type': settings.get('availabilityType', ''),
    }


def get_infrastructure_data() -> Dict[str, Any]:
    """
    Raccoglie tutte le metriche infrastrutturali in un'unica chiamata.
    Esegue kubectl e gcloud in sequenza (~5-10 secondi totali).
    """
    return {
        'pods_metrics': get_pod_metrics(),
        'nodes_metrics': get_node_metrics(),
        'hpa': get_hpa_status(),
        'deployment': get_deployment_info(),
        'pods_status': get_pods_status(),
        'cloud_sql': get_cloud_sql_info(),
    }
