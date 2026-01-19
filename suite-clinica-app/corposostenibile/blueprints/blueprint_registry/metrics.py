"""Calcolo metriche automatiche blueprint"""
from datetime import datetime, timedelta
from sqlalchemy import func, distinct
from corposostenibile.extensions import db
from corposostenibile.models import GlobalActivityLog, User


def calculate_adoption_metrics(blueprint_code: str) -> dict:
    """Calcola metriche adoption automatiche per un blueprint."""

    # Total eligible users (tutti gli utenti attivi)
    total_users = User.query.filter_by(is_active=True).count()

    # Active users oggi
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    active_users_today = db.session.query(
        func.count(distinct(GlobalActivityLog.user_id))
    ).filter(
        GlobalActivityLog.blueprint == blueprint_code,
        GlobalActivityLog.created_at >= today_start,
        GlobalActivityLog.user_id.isnot(None)
    ).scalar() or 0

    # Active users ultimi 30 giorni (per adoption rate)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    active_users_30d = db.session.query(
        func.count(distinct(GlobalActivityLog.user_id))
    ).filter(
        GlobalActivityLog.blueprint == blueprint_code,
        GlobalActivityLog.created_at >= thirty_days_ago,
        GlobalActivityLog.user_id.isnot(None)
    ).scalar() or 0

    # Calcolo adoption rate (% utenti attivi ultimi 30 giorni / totale utenti)
    adoption_rate = (active_users_30d / total_users * 100) if total_users > 0 else 0

    # Avg daily requests (media ultimi 7 giorni)
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    total_requests_7d = db.session.query(
        func.count(GlobalActivityLog.id)
    ).filter(
        GlobalActivityLog.blueprint == blueprint_code,
        GlobalActivityLog.created_at >= seven_days_ago
    ).scalar() or 0
    avg_daily_requests = total_requests_7d // 7

    # Error rate (ultimi 7 giorni)
    error_requests = db.session.query(
        func.count(GlobalActivityLog.id)
    ).filter(
        GlobalActivityLog.blueprint == blueprint_code,
        GlobalActivityLog.created_at >= seven_days_ago,
        GlobalActivityLog.http_status >= 400
    ).scalar() or 0

    error_rate = (error_requests / total_requests_7d * 100) if total_requests_7d > 0 else 0

    # Avg response time
    avg_response_time = db.session.query(
        func.avg(GlobalActivityLog.response_time_ms)
    ).filter(
        GlobalActivityLog.blueprint == blueprint_code,
        GlobalActivityLog.created_at >= seven_days_ago,
        GlobalActivityLog.response_time_ms.isnot(None)
    ).scalar() or 0

    return {
        "total_users": total_users,
        "active_users_today": active_users_today,
        "active_users_30d": active_users_30d,
        "adoption_rate": round(adoption_rate, 2),
        "avg_daily_requests": avg_daily_requests,
        "error_rate": round(error_rate, 2),
        "avg_response_time_ms": int(avg_response_time) if avg_response_time else 0
    }


def get_metrics_history_30d(blueprint_code: str) -> dict:
    """Calcola metriche giornaliere degli ultimi 30 giorni per i grafici."""

    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    # Array per i risultati
    dates = []
    active_users = []
    daily_requests = []
    error_rates = []
    avg_response_times = []

    # Calcola metriche per ogni giorno degli ultimi 30 giorni
    for i in range(30):
        day_start = (datetime.utcnow() - timedelta(days=29-i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        # Data label
        dates.append(day_start.strftime('%Y-%m-%d'))

        # Active users del giorno
        users_count = db.session.query(
            func.count(distinct(GlobalActivityLog.user_id))
        ).filter(
            GlobalActivityLog.blueprint == blueprint_code,
            GlobalActivityLog.created_at >= day_start,
            GlobalActivityLog.created_at < day_end,
            GlobalActivityLog.user_id.isnot(None)
        ).scalar() or 0
        active_users.append(users_count)

        # Requests del giorno
        requests_count = db.session.query(
            func.count(GlobalActivityLog.id)
        ).filter(
            GlobalActivityLog.blueprint == blueprint_code,
            GlobalActivityLog.created_at >= day_start,
            GlobalActivityLog.created_at < day_end
        ).scalar() or 0
        daily_requests.append(requests_count)

        # Error rate del giorno
        error_count = db.session.query(
            func.count(GlobalActivityLog.id)
        ).filter(
            GlobalActivityLog.blueprint == blueprint_code,
            GlobalActivityLog.created_at >= day_start,
            GlobalActivityLog.created_at < day_end,
            GlobalActivityLog.http_status >= 400
        ).scalar() or 0

        error_rate = (error_count / requests_count * 100) if requests_count > 0 else 0
        error_rates.append(round(error_rate, 2))

        # Avg response time del giorno
        avg_resp = db.session.query(
            func.avg(GlobalActivityLog.response_time_ms)
        ).filter(
            GlobalActivityLog.blueprint == blueprint_code,
            GlobalActivityLog.created_at >= day_start,
            GlobalActivityLog.created_at < day_end,
            GlobalActivityLog.response_time_ms.isnot(None)
        ).scalar() or 0
        avg_response_times.append(int(avg_resp) if avg_resp else 0)

    return {
        "dates": dates,
        "active_users": active_users,
        "daily_requests": daily_requests,
        "error_rates": error_rates,
        "avg_response_times": avg_response_times
    }


def get_adoption_level(adoption_rate: float) -> str:
    """Determina adoption level basato sul rate."""
    if adoption_rate >= 80:
        return "critical"
    elif adoption_rate >= 50:
        return "high"
    elif adoption_rate >= 20:
        return "medium"
    elif adoption_rate > 0:
        return "low"
    else:
        return "none"
