"""Routes Database Registry"""
from flask import render_template, request
from flask_login import login_required
from . import bp
from .analyzer import (
    get_all_models, get_model_info, get_database_stats,
    format_storage_size, calculate_growth_rate
)


@bp.route('/')
@login_required
def index():
    """Dashboard principale Database Models."""
    # Parametro per ordinamento
    sort_by = request.args.get('sort_by', 'table_name')  # table_name, total_records, storage
    sort_order = request.args.get('sort_order', 'asc')  # asc, desc

    # Ottieni tutti i modelli
    models = get_all_models()

    # Genera info per ogni modello
    models_info = []
    for model in models:
        info = get_model_info(model)
        info['storage_formatted'] = format_storage_size(info['storage_bytes'])

        if info['created_last_7d'] is not None and info['created_last_30d'] is not None:
            info['growth_rate'] = calculate_growth_rate(
                info['created_last_7d'],
                info['created_last_30d']
            )
        else:
            info['growth_rate'] = None

        models_info.append(info)

    # Ordina modelli
    if sort_by == 'total_records':
        models_info.sort(key=lambda x: x['total_records'], reverse=(sort_order == 'desc'))
    elif sort_by == 'storage':
        models_info.sort(key=lambda x: x['storage_bytes'] or 0, reverse=(sort_order == 'desc'))
    elif sort_by == 'activity':
        models_info.sort(key=lambda x: x['created_today'] or 0, reverse=(sort_order == 'desc'))
    else:  # table_name
        models_info.sort(key=lambda x: x['table_name'], reverse=(sort_order == 'desc'))

    # Statistiche globali
    stats = get_database_stats()
    stats['total_storage_formatted'] = format_storage_size(stats['total_storage_bytes'])

    return render_template('database_registry/index.html',
                         models=models_info,
                         stats=stats,
                         sort_by=sort_by,
                         sort_order=sort_order)


@bp.route('/<string:table_name>')
@login_required
def detail(table_name):
    """Dettaglio modello specifico."""
    # Trova modello per table_name
    models = get_all_models()
    model = None
    for m in models:
        if m.__tablename__ == table_name:
            model = m
            break

    if not model:
        from flask import abort
        abort(404)

    # Info dettagliate
    info = get_model_info(model)
    info['storage_formatted'] = format_storage_size(info['storage_bytes'])

    if info['created_last_7d'] is not None and info['created_last_30d'] is not None:
        info['growth_rate'] = calculate_growth_rate(
            info['created_last_7d'],
            info['created_last_30d']
        )
    else:
        info['growth_rate'] = None

    # Ottieni info su colonne e relazioni
    from sqlalchemy.orm import class_mapper
    mapper = class_mapper(model)

    columns_info = []
    for col in mapper.mapped_table.columns:
        columns_info.append({
            'name': col.name,
            'type': str(col.type),
            'nullable': col.nullable,
            'primary_key': col.primary_key,
            'foreign_key': bool(col.foreign_keys),
        })

    relationships_info = []
    for rel in mapper.relationships:
        relationships_info.append({
            'name': rel.key,
            'target': rel.mapper.class_.__name__,
            'direction': rel.direction.name,
        })

    return render_template('database_registry/detail.html',
                         model_info=info,
                         columns=columns_info,
                         relationships=relationships_info)
