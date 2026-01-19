"""
API REST per funzionalità AJAX del modulo Nutrition
"""

from datetime import datetime
from flask import jsonify, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, func

from corposostenibile.extensions import db
from corposostenibile.models import (
    Food, FoodCategory, Recipe, RecipeIngredient,
    MealPlan, MealPlanDay, Meal, MealFood,
    MealTypeEnum, FoodUnitEnum
)
from . import bp


# ===== API RICERCA ALIMENTI =====
@bp.route('/api/foods/search')
@login_required
def api_food_search():
    """Ricerca alimenti con autocomplete."""
    query = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    limit = request.args.get('limit', 20, type=int)
    
    if len(query) < 2:
        return jsonify({'results': []})
    
    foods_query = Food.query.filter(
        or_(
            Food.name.ilike(f'%{query}%'),
            Food.brand.ilike(f'%{query}%')
        )
    )
    
    if category_id:
        foods_query = foods_query.filter_by(category_id=category_id)
    
    foods = foods_query.limit(limit).all()
    
    results = [{
        'id': food.id,
        'name': food.name,
        'brand': food.brand,
        'calories': food.calories,
        'proteins': food.proteins,
        'carbohydrates': food.carbohydrates,
        'fats': food.fats,
        'category': food.category.name if food.category else None
    } for food in foods]
    
    return jsonify({'results': results})


@bp.route('/api/foods/<int:food_id>')
@login_required
def api_food_detail(food_id):
    """Dettagli completi alimento."""
    food = Food.query.get_or_404(food_id)
    
    return jsonify({
        'id': food.id,
        'name': food.name,
        'brand': food.brand,
        'calories': food.calories,
        'proteins': food.proteins,
        'carbohydrates': food.carbohydrates,
        'fats': food.fats,
        'fibers': food.fibers,
        'sugars': food.sugars,
        'saturated_fats': food.saturated_fats,
        'sodium': food.sodium,
        'micronutrients': food.micronutrients or {},
        'units': [
            {'value': unit.value, 'label': unit.name} 
            for unit in FoodUnitEnum
        ]
    })


# ===== API GESTIONE PASTI =====
@bp.route('/api/meal-plans/<int:plan_id>/days/<int:day_id>/meals', methods=['POST'])
@login_required
def api_create_meal(plan_id, day_id):
    """Crea nuovo pasto in un giorno."""
    plan = MealPlan.query.get_or_404(plan_id)
    day = MealPlanDay.query.get_or_404(day_id)
    
    # Verifica permessi
    if plan.created_by_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    if day.meal_plan_id != plan_id:
        abort(400)
    
    data = request.get_json()
    meal_type = data.get('meal_type')
    
    # Valida meal_type
    if meal_type not in [mt.value for mt in MealTypeEnum]:
        return jsonify({'error': 'Tipo pasto non valido'}), 400
    
    # Verifica se esiste già un pasto di questo tipo
    existing = Meal.query.filter_by(
        meal_plan_day_id=day_id,
        meal_type=meal_type
    ).first()
    
    if existing:
        return jsonify({'error': 'Pasto già esistente per questo tipo'}), 400
    
    meal = Meal(
        meal_plan_day_id=day_id,
        meal_type=meal_type,
        name=data.get('name', '')
    )
    
    db.session.add(meal)
    db.session.commit()
    
    return jsonify({
        'id': meal.id,
        'meal_type': meal.meal_type,
        'name': meal.name,
        'foods': []
    })


@bp.route('/api/meals/<int:meal_id>/foods', methods=['POST'])
@login_required
def api_add_meal_food(meal_id):
    """Aggiungi alimento a un pasto."""
    meal = Meal.query.get_or_404(meal_id)
    plan = meal.meal_plan_day.meal_plan
    
    # Verifica permessi
    if plan.created_by_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    data = request.get_json()
    
    # Validazione
    if not data.get('food_id') and not data.get('recipe_id'):
        return jsonify({'error': 'Specificare food_id o recipe_id'}), 400
    
    if data.get('food_id') and data.get('recipe_id'):
        return jsonify({'error': 'Specificare solo uno tra food_id e recipe_id'}), 400
    
    quantity = data.get('quantity', 100)
    unit = data.get('unit', 'g')
    
    # Valida unit
    if unit not in [u.value for u in FoodUnitEnum]:
        return jsonify({'error': 'Unità non valida'}), 400
    
    meal_food = MealFood(
        meal_id=meal_id,
        food_id=data.get('food_id'),
        recipe_id=data.get('recipe_id'),
        quantity=quantity,
        unit=unit,
        notes=data.get('notes', '')
    )
    
    db.session.add(meal_food)
    db.session.commit()
    
    # Ritorna dati calcolati
    response_data = {
        'id': meal_food.id,
        'quantity': meal_food.quantity,
        'unit': meal_food.unit,
        'calories': meal_food.calories,
        'proteins': meal_food.proteins,
        'carbohydrates': meal_food.carbohydrates,
        'fats': meal_food.fats
    }
    
    if meal_food.food:
        response_data['food'] = {
            'id': meal_food.food.id,
            'name': meal_food.food.name,
            'brand': meal_food.food.brand
        }
    elif meal_food.recipe:
        response_data['recipe'] = {
            'id': meal_food.recipe.id,
            'name': meal_food.recipe.name
        }
    
    return jsonify(response_data)


@bp.route('/api/meal-foods/<int:meal_food_id>', methods=['PUT'])
@login_required
def api_update_meal_food(meal_food_id):
    """Aggiorna quantità alimento nel pasto."""
    meal_food = MealFood.query.get_or_404(meal_food_id)
    plan = meal_food.meal.meal_plan_day.meal_plan
    
    # Verifica permessi
    if plan.created_by_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    data = request.get_json()
    
    if 'quantity' in data:
        meal_food.quantity = data['quantity']
    
    if 'unit' in data:
        if data['unit'] in [u.value for u in FoodUnitEnum]:
            meal_food.unit = data['unit']
    
    if 'notes' in data:
        meal_food.notes = data['notes']
    
    db.session.commit()
    
    return jsonify({
        'id': meal_food.id,
        'quantity': meal_food.quantity,
        'unit': meal_food.unit,
        'calories': meal_food.calories,
        'proteins': meal_food.proteins,
        'carbohydrates': meal_food.carbohydrates,
        'fats': meal_food.fats
    })


@bp.route('/api/meal-foods/<int:meal_food_id>', methods=['DELETE'])
@login_required
def api_delete_meal_food(meal_food_id):
    """Rimuovi alimento dal pasto."""
    meal_food = MealFood.query.get_or_404(meal_food_id)
    plan = meal_food.meal.meal_plan_day.meal_plan
    
    # Verifica permessi
    if plan.created_by_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    db.session.delete(meal_food)
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/api/meals/<int:meal_id>', methods=['DELETE'])
@login_required
def api_delete_meal(meal_id):
    """Elimina pasto completo."""
    meal = Meal.query.get_or_404(meal_id)
    plan = meal.meal_plan_day.meal_plan
    
    # Verifica permessi
    if plan.created_by_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    db.session.delete(meal)
    db.session.commit()
    
    return jsonify({'success': True})


# ===== API RICETTE =====
@bp.route('/api/recipes/<int:recipe_id>/ingredients', methods=['POST'])
@login_required
def api_add_recipe_ingredient(recipe_id):
    """Aggiungi ingrediente a ricetta."""
    recipe = Recipe.query.get_or_404(recipe_id)
    
    # Verifica permessi
    if recipe.created_by_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    data = request.get_json()
    
    if not data.get('food_id'):
        return jsonify({'error': 'food_id richiesto'}), 400
    
    # Trova l'ordine massimo
    max_order = db.session.query(func.max(RecipeIngredient.order_index)).filter_by(
        recipe_id=recipe_id
    ).scalar() or 0
    
    ingredient = RecipeIngredient(
        recipe_id=recipe_id,
        food_id=data['food_id'],
        quantity=data.get('quantity', 100),
        unit=data.get('unit', 'g'),
        notes=data.get('notes', ''),
        order_index=max_order + 1
    )
    
    db.session.add(ingredient)
    db.session.commit()
    
    return jsonify({
        'id': ingredient.id,
        'food': {
            'id': ingredient.food.id,
            'name': ingredient.food.name
        },
        'quantity': ingredient.quantity,
        'unit': ingredient.unit,
        'calories': ingredient.calories,
        'proteins': ingredient.proteins,
        'carbohydrates': ingredient.carbohydrates,
        'fats': ingredient.fats
    })


@bp.route('/api/recipe-ingredients/<int:ingredient_id>', methods=['PUT'])
@login_required
def api_update_recipe_ingredient(ingredient_id):
    """Aggiorna ingrediente ricetta."""
    ingredient = RecipeIngredient.query.get_or_404(ingredient_id)
    
    # Verifica permessi
    if ingredient.recipe.created_by_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    data = request.get_json()
    
    if 'quantity' in data:
        ingredient.quantity = data['quantity']
    
    if 'unit' in data:
        ingredient.unit = data['unit']
    
    if 'notes' in data:
        ingredient.notes = data['notes']
    
    db.session.commit()
    
    return jsonify({'success': True})


@bp.route('/api/recipe-ingredients/<int:ingredient_id>', methods=['DELETE'])
@login_required
def api_delete_recipe_ingredient(ingredient_id):
    """Rimuovi ingrediente da ricetta."""
    ingredient = RecipeIngredient.query.get_or_404(ingredient_id)
    
    # Verifica permessi
    if ingredient.recipe.created_by_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    db.session.delete(ingredient)
    db.session.commit()
    
    return jsonify({'success': True})


# ===== API TEMPLATE =====
@bp.route('/api/meal-plans/<int:plan_id>/save-template', methods=['POST'])
@login_required
def api_save_template(plan_id):
    """Salva piano come template."""
    plan = MealPlan.query.get_or_404(plan_id)
    
    # Verifica permessi
    if plan.created_by_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    data = request.get_json()
    
    # Serializza struttura del piano
    template_data = {
        'days': []
    }
    
    days = MealPlanDay.query.filter_by(
        meal_plan_id=plan_id
    ).order_by(MealPlanDay.day_number).all()
    
    for day in days:
        day_data = {
            'day_number': day.day_number,
            'meals': []
        }
        
        for meal in day.meals:
            meal_data = {
                'meal_type': meal.meal_type,
                'name': meal.name,
                'foods': []
            }
            
            for mf in meal.foods:
                food_data = {
                    'food_id': mf.food_id,
                    'recipe_id': mf.recipe_id,
                    'quantity': mf.quantity,
                    'unit': mf.unit,
                    'notes': mf.notes
                }
                meal_data['foods'].append(food_data)
            
            day_data['meals'].append(meal_data)
        
        template_data['days'].append(day_data)
    
    # Crea template
    from corposostenibile.models import MealPlanTemplate
    
    template = MealPlanTemplate(
        name=data.get('name', f'Template da {plan.name}'),
        description=data.get('description', ''),
        duration_days=len(days),
        tags=data.get('tags', []),
        target_calories=plan.target_calories,
        target_proteins=plan.target_proteins,
        target_carbohydrates=plan.target_carbohydrates,
        target_fats=plan.target_fats,
        created_by_id=current_user.id,
        is_public=data.get('is_public', False),
        template_data=template_data
    )
    
    db.session.add(template)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'template_id': template.id
    })


@bp.route('/api/meal-plans/<int:plan_id>/apply-template/<int:template_id>', methods=['POST'])
@login_required
def api_apply_template(plan_id, template_id):
    """Applica template a piano esistente."""
    plan = MealPlan.query.get_or_404(plan_id)
    template = MealPlanTemplate.query.get_or_404(template_id)
    
    # Verifica permessi
    if plan.created_by_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    if not template.is_public and template.created_by_id != current_user.id:
        abort(403)
    
    try:
        # Ottieni giorni del piano
        days = MealPlanDay.query.filter_by(
            meal_plan_id=plan_id
        ).order_by(MealPlanDay.day_number).all()
        
        # Applica template
        template_days = template.template_data.get('days', [])
        
        for i, day in enumerate(days):
            if i >= len(template_days):
                break
            
            template_day = template_days[i]
            
            # Rimuovi pasti esistenti
            Meal.query.filter_by(meal_plan_day_id=day.id).delete()
            
            # Crea nuovi pasti dal template
            for template_meal in template_day['meals']:
                meal = Meal(
                    meal_plan_day_id=day.id,
                    meal_type=template_meal['meal_type'],
                    name=template_meal.get('name', '')
                )
                db.session.add(meal)
                db.session.flush()
                
                # Aggiungi alimenti
                for template_food in template_meal['foods']:
                    meal_food = MealFood(
                        meal_id=meal.id,
                        food_id=template_food.get('food_id'),
                        recipe_id=template_food.get('recipe_id'),
                        quantity=template_food['quantity'],
                        unit=template_food['unit'],
                        notes=template_food.get('notes', '')
                    )
                    db.session.add(meal_food)
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ===== API STATISTICHE =====
@bp.route('/api/meal-plans/<int:plan_id>/stats')
@login_required
def api_meal_plan_stats(plan_id):
    """Statistiche nutrizionali del piano."""
    plan = MealPlan.query.get_or_404(plan_id)
    
    # Verifica permessi
    if not current_user.is_admin:
        if hasattr(current_user, 'cliente_id'):
            if plan.cliente_id != current_user.cliente_id:
                abort(403)
        elif plan.created_by_id != current_user.id:
            abort(403)
    
    # Calcola statistiche per ogni giorno
    days_stats = []
    
    days = MealPlanDay.query.filter_by(
        meal_plan_id=plan_id
    ).order_by(MealPlanDay.day_date).all()
    
    for day in days:
        day_stats = {
            'date': day.day_date.isoformat(),
            'calories': 0,
            'proteins': 0,
            'carbohydrates': 0,
            'fats': 0,
            'meals': {}
        }
        
        for meal in day.meals:
            meal_stats = {
                'calories': meal.total_calories,
                'proteins': meal.total_proteins,
                'carbohydrates': meal.total_carbohydrates,
                'fats': meal.total_fats
            }
            
            day_stats['meals'][meal.meal_type] = meal_stats
            day_stats['calories'] += meal_stats['calories']
            day_stats['proteins'] += meal_stats['proteins']
            day_stats['carbohydrates'] += meal_stats['carbohydrates']
            day_stats['fats'] += meal_stats['fats']
        
        days_stats.append(day_stats)
    
    # Media
    if days_stats:
        avg_stats = {
            'calories': sum(d['calories'] for d in days_stats) / len(days_stats),
            'proteins': sum(d['proteins'] for d in days_stats) / len(days_stats),
            'carbohydrates': sum(d['carbohydrates'] for d in days_stats) / len(days_stats),
            'fats': sum(d['fats'] for d in days_stats) / len(days_stats)
        }
    else:
        avg_stats = {
            'calories': 0,
            'proteins': 0,
            'carbohydrates': 0,
            'fats': 0
        }
    
    return jsonify({
        'plan': {
            'target_calories': plan.target_calories,
            'target_proteins': plan.target_proteins,
            'target_carbohydrates': plan.target_carbohydrates,
            'target_fats': plan.target_fats
        },
        'average': avg_stats,
        'daily': days_stats
    })