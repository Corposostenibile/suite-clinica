"""
Database Models Analyzer
=========================
Analizza automaticamente tutti i modelli SQLAlchemy e genera statistiche.
"""
from datetime import datetime, timedelta
from sqlalchemy import inspect, func, text
from sqlalchemy.orm import class_mapper
from corposostenibile.extensions import db
from corposostenibile.models import TimestampMixin


def get_all_models():
    """Ottiene tutti i modelli SQLAlchemy registrati."""
    models = []
    for mapper in db.Model.registry.mappers:
        model_class = mapper.class_
        # Salta modelli di versioning (continuum)
        if 'Version' in model_class.__name__:
            continue
        models.append(model_class)

    return sorted(models, key=lambda m: m.__tablename__)


def get_model_info(model_class):
    """Ottiene informazioni dettagliate su un modello."""
    mapper = class_mapper(model_class)
    table = mapper.mapped_table

    # Info base
    info = {
        'class_name': model_class.__name__,
        'table_name': table.name,
        'has_timestamps': issubclass(model_class, TimestampMixin),
        'columns_count': len(table.columns),
        'relationships_count': len(mapper.relationships),
    }

    # Count totale record
    try:
        info['total_records'] = db.session.query(func.count()).select_from(model_class).scalar() or 0
    except Exception as e:
        info['total_records'] = 0
        info['error'] = str(e)

    # Stats temporali (solo se ha TimestampMixin)
    if info['has_timestamps']:
        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = datetime.utcnow() - timedelta(days=7)
            month_ago = datetime.utcnow() - timedelta(days=30)

            info['created_today'] = db.session.query(func.count()).select_from(model_class).filter(
                model_class.created_at >= today_start
            ).scalar() or 0

            info['created_last_7d'] = db.session.query(func.count()).select_from(model_class).filter(
                model_class.created_at >= week_ago
            ).scalar() or 0

            info['created_last_30d'] = db.session.query(func.count()).select_from(model_class).filter(
                model_class.created_at >= month_ago
            ).scalar() or 0

            # Ultimo record creato
            last_record = db.session.query(model_class.created_at).order_by(
                model_class.created_at.desc()
            ).first()
            info['last_created_at'] = last_record[0] if last_record else None

            # Primo record creato
            first_record = db.session.query(model_class.created_at).order_by(
                model_class.created_at.asc()
            ).first()
            info['first_created_at'] = first_record[0] if first_record else None

        except Exception as e:
            info['created_today'] = 0
            info['created_last_7d'] = 0
            info['created_last_30d'] = 0
            info['last_created_at'] = None
            info['first_created_at'] = None
    else:
        info['created_today'] = None
        info['created_last_7d'] = None
        info['created_last_30d'] = None
        info['last_created_at'] = None
        info['first_created_at'] = None

    # Storage size (solo PostgreSQL)
    try:
        result = db.session.execute(
            text(f"SELECT pg_total_relation_size('{table.name}')::bigint")
        ).scalar()
        info['storage_bytes'] = result if result else 0
    except Exception:
        info['storage_bytes'] = None

    return info


def get_database_stats():
    """Statistiche globali database."""
    models = get_all_models()

    total_records = 0
    total_storage = 0
    models_with_data = 0
    largest_table = None
    largest_table_count = 0
    most_active_table = None
    most_active_count = 0

    for model in models:
        info = get_model_info(model)

        if info['total_records'] > 0:
            models_with_data += 1
            total_records += info['total_records']

            if info['total_records'] > largest_table_count:
                largest_table_count = info['total_records']
                largest_table = info

        if info['created_today'] and info['created_today'] > most_active_count:
            most_active_count = info['created_today']
            most_active_table = info

        if info['storage_bytes']:
            total_storage += info['storage_bytes']

    return {
        'total_models': len(models),
        'models_with_data': models_with_data,
        'total_records': total_records,
        'total_storage_bytes': total_storage,
        'largest_table': largest_table,
        'most_active_table': most_active_table,
    }


def format_storage_size(bytes_size):
    """Formatta dimensione storage in formato leggibile."""
    if bytes_size is None:
        return "N/A"

    if bytes_size < 1024:
        return f"{bytes_size} B"
    elif bytes_size < 1024 * 1024:
        return f"{bytes_size / 1024:.1f} KB"
    elif bytes_size < 1024 * 1024 * 1024:
        return f"{bytes_size / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_size / (1024 * 1024 * 1024):.2f} GB"


def calculate_growth_rate(created_last_7d, created_last_30d):
    """Calcola il trend di crescita."""
    if not created_last_30d or created_last_30d == 0:
        return 0

    # Media giornaliera ultimi 7 giorni vs ultimi 30 giorni
    avg_7d = created_last_7d / 7
    avg_30d = created_last_30d / 30

    if avg_30d == 0:
        return 0

    growth = ((avg_7d - avg_30d) / avg_30d) * 100
    return round(growth, 1)
