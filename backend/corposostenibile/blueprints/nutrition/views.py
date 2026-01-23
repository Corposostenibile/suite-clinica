"""
Views principali del modulo Nutrition
"""

from datetime import date, datetime, timedelta
from flask import (
    render_template, redirect, url_for, flash, request,
    jsonify, current_app, abort, send_file
)
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import joinedload

from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente, User,
    Food, FoodCategory, Recipe, RecipeIngredient,
    MealPlan, MealPlanDay, Meal, MealFood,
    MealPlanTemplate, NutritionalProfile, HealthAssessment,
    BiometricData, DietaryPreference, FoodIntolerance,
    NutritionNote
)
from . import bp
from .forms import (
    NutritionalProfileForm, HealthAssessmentForm, BiometricDataForm,
    MealPlanForm, RecipeForm, FoodForm, NutritionNoteForm
)
from .utils import calculate_tdee, calculate_bmr, generate_meal_plan_pdf
from .pdf import create_meal_plan_pdf


# ===== DASHBOARD =====
@bp.route('/')
@login_required
def dashboard():
    """Dashboard principale nutrition."""
    # Statistiche per la nutrizionista
    stats = {
        'total_clients': Cliente.query.join(NutritionalProfile).count(),
        'active_plans': MealPlan.query.filter_by(is_active=True).count(),
        'recipes': Recipe.query.filter_by(created_by_id=current_user.id).count(),
        'foods': Food.query.count()
    }
    
    # Clienti con piani in scadenza
    expiring_plans = db.session.query(MealPlan, Cliente).join(
        Cliente, MealPlan.cliente_id == Cliente.cliente_id
    ).filter(
        MealPlan.is_active == True,
        MealPlan.end_date <= date.today() + timedelta(days=7),
        MealPlan.end_date >= date.today()
    ).order_by(MealPlan.end_date).limit(10).all()
    
    # Ultimi aggiornamenti
    recent_assessments = db.session.query(HealthAssessment, Cliente).join(
        Cliente, HealthAssessment.cliente_id == Cliente.cliente_id
    ).order_by(HealthAssessment.assessment_date.desc()).limit(5).all()
    
    return render_template('nutrition/dashboard.html',
                         stats=stats,
                         expiring_plans=expiring_plans,
                         recent_assessments=recent_assessments)


# ===== CLIENTI =====
@bp.route('/clients')
@login_required
def client_list():
    """Lista clienti con profilo nutrizionale."""
    search = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    
    query = Cliente.query.join(
        NutritionalProfile, 
        Cliente.cliente_id == NutritionalProfile.cliente_id,
        isouter=True
    )
    
    if search:
        query = query.filter(
            or_(
                Cliente.nome_cognome.ilike(f'%{search}%'),
                Cliente.consulente_alimentare.ilike(f'%{search}%')
            )
        )
    
    # Filtra per nutrizionista se non è admin
    if not current_user.is_admin:
        from corposostenibile.models import NutrizionistaEnum
        # Trova l'enum corrispondente al nome dell'utente
        nutritionist_name = current_user.full_name.lower().replace(' ', '_')
        query = query.filter(
            Cliente.nutrizionista.any(nutritionist_name)
        )
    
    clients = query.order_by(Cliente.nome_cognome).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('nutrition/clients/list.html', clients=clients)


@bp.route('/clients/<int:cliente_id>')
@login_required
def client_profile(cliente_id):
    """Profilo nutrizionale completo del cliente."""
    cliente = Cliente.query.get_or_404(cliente_id)
    
    # Verifica permessi
    if not current_user.is_admin:
        nutritionist_name = current_user.full_name.lower().replace(' ', '_')
        if not cliente.nutrizionista or nutritionist_name not in cliente.nutrizionista:
            abort(403)
    
    # Carica tutti i dati correlati
    profile = NutritionalProfile.query.filter_by(cliente_id=cliente_id).first()
    latest_assessment = HealthAssessment.query.filter_by(
        cliente_id=cliente_id
    ).order_by(HealthAssessment.assessment_date.desc()).first()
    
    latest_biometric = BiometricData.query.filter_by(
        cliente_id=cliente_id
    ).order_by(BiometricData.measurement_date.desc()).first()
    
    active_plan = MealPlan.query.filter_by(
        cliente_id=cliente_id,
        is_active=True
    ).first()
    
    # Storico biometrico per grafici
    biometric_history = BiometricData.query.filter_by(
        cliente_id=cliente_id
    ).order_by(BiometricData.measurement_date.desc()).limit(12).all()
    
    # Note nutrizionista
    notes = NutritionNote.query.filter_by(
        cliente_id=cliente_id
    ).order_by(NutritionNote.note_date.desc()).limit(10).all()
    
    return render_template('nutrition/clients/profile.html',
                         cliente=cliente,
                         profile=profile,
                         assessment=latest_assessment,
                         biometric=latest_biometric,
                         active_plan=active_plan,
                         biometric_history=biometric_history,
                         notes=notes)


@bp.route('/clients/<int:cliente_id>/assessment', methods=['GET', 'POST'])
@login_required
def client_assessment(cliente_id):
    """Crea/aggiorna anamnesi salute."""
    cliente = Cliente.query.get_or_404(cliente_id)
    
    # Verifica permessi
    if not current_user.is_admin:
        nutritionist_name = current_user.full_name.lower().replace(' ', '_')
        if not cliente.nutrizionista or nutritionist_name not in cliente.nutrizionista:
            abort(403)
    
    # Carica assessment esistente se presente
    assessment = HealthAssessment.query.filter_by(
        cliente_id=cliente_id
    ).order_by(HealthAssessment.assessment_date.desc()).first()
    
    form = HealthAssessmentForm(obj=assessment)
    
    if form.validate_on_submit():
        if not assessment:
            assessment = HealthAssessment(cliente_id=cliente_id)
            db.session.add(assessment)
        
        form.populate_obj(assessment)
        assessment.assessment_date = date.today()
        
        try:
            db.session.commit()
            flash('Anamnesi salvata con successo', 'success')
            return redirect(url_for('nutrition.client_profile', cliente_id=cliente_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nel salvataggio: {str(e)}', 'danger')
    
    return render_template('nutrition/clients/assessment.html',
                         cliente=cliente,
                         form=form,
                         assessment=assessment)


# ===== PIANI ALIMENTARI =====
@bp.route('/meal-plans')
@login_required
def meal_plan_list():
    """Lista piani alimentari."""
    page = request.args.get('page', 1, type=int)
    filter_active = request.args.get('active', 'all')
    
    query = MealPlan.query.join(Cliente)
    
    # Filtri
    if filter_active == 'active':
        query = query.filter(MealPlan.is_active == True)
    elif filter_active == 'inactive':
        query = query.filter(MealPlan.is_active == False)
    
    # Solo piani creati dall'utente se non admin
    if not current_user.is_admin:
        query = query.filter(MealPlan.created_by_id == current_user.id)
    
    plans = query.order_by(MealPlan.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('nutrition/meal_plans/list.html', plans=plans)


@bp.route('/meal-plans/create/<int:cliente_id>', methods=['GET', 'POST'])
@login_required
def meal_plan_create(cliente_id):
    """Crea nuovo piano alimentare."""
    cliente = Cliente.query.get_or_404(cliente_id)
    
    # Verifica permessi
    if not current_user.is_admin:
        nutritionist_name = current_user.full_name.lower().replace(' ', '_')
        if not cliente.nutrizionista or nutritionist_name not in cliente.nutrizionista:
            abort(403)
    
    form = MealPlanForm()
    
    # Carica profilo nutrizionale per suggerimenti
    profile = NutritionalProfile.query.filter_by(cliente_id=cliente_id).first()
    if profile:
        # Calcola TDEE e suggerisci valori
        latest_bio = BiometricData.query.filter_by(
            cliente_id=cliente_id
        ).order_by(BiometricData.measurement_date.desc()).first()
        
        if latest_bio:
            bmr = calculate_bmr(
                weight=latest_bio.weight,
                height=latest_bio.height,
                age=cliente.age,
                gender=profile.gender
            )
            tdee = calculate_tdee(bmr, profile.activity_level)
            
            # Suggerisci macros in base all'obiettivo
            if not form.target_calories.data:
                if profile.nutritional_goal.value == 'dimagrimento':
                    form.target_calories.data = int(tdee * 0.8)  # -20%
                elif profile.nutritional_goal.value == 'aumento_massa':
                    form.target_calories.data = int(tdee * 1.1)  # +10%
                else:
                    form.target_calories.data = int(tdee)
    
    if form.validate_on_submit():
        plan = MealPlan(
            cliente_id=cliente_id,
            created_by_id=current_user.id,
            name=form.name.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            target_calories=form.target_calories.data,
            target_proteins=form.target_proteins.data,
            target_carbohydrates=form.target_carbohydrates.data,
            target_fats=form.target_fats.data,
            notes=form.notes.data,
            is_active=True
        )
        
        # Disattiva altri piani attivi
        MealPlan.query.filter_by(
            cliente_id=cliente_id,
            is_active=True
        ).update({'is_active': False})
        
        db.session.add(plan)
        
        try:
            db.session.commit()
            
            # Crea giorni del piano
            current_date = plan.start_date
            day_number = 1
            while current_date <= plan.end_date:
                day = MealPlanDay(
                    meal_plan_id=plan.id,
                    day_date=current_date,
                    day_number=day_number
                )
                db.session.add(day)
                current_date += timedelta(days=1)
                day_number += 1
            
            db.session.commit()
            flash('Piano alimentare creato con successo', 'success')
            return redirect(url_for('nutrition.meal_plan_editor', plan_id=plan.id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nella creazione: {str(e)}', 'danger')
    
    return render_template('nutrition/meal_plans/create.html',
                         cliente=cliente,
                         form=form,
                         profile=profile)


@bp.route('/meal-plans/<int:plan_id>/edit')
@login_required
def meal_plan_editor(plan_id):
    """Editor drag-drop per il piano alimentare."""
    plan = MealPlan.query.get_or_404(plan_id)
    
    # Verifica permessi
    if not current_user.is_admin and plan.created_by_id != current_user.id:
        abort(403)
    
    # Carica tutti i giorni con pasti
    days = MealPlanDay.query.filter_by(
        meal_plan_id=plan_id
    ).options(
        joinedload(MealPlanDay.meals).joinedload(Meal.foods)
    ).order_by(MealPlanDay.day_date).all()
    
    # Categorie alimenti per sidebar
    categories = FoodCategory.query.filter_by(parent_id=None).all()
    
    # Template salvati
    templates = MealPlanTemplate.query.filter(
        or_(
            MealPlanTemplate.is_public == True,
            MealPlanTemplate.created_by_id == current_user.id
        )
    ).all()
    
    return render_template('nutrition/meal_plans/editor.html',
                         plan=plan,
                         days=days,
                         categories=categories,
                         templates=templates)


@bp.route('/meal-plans/<int:plan_id>/view')
@login_required
def meal_plan_view(plan_id):
    """Visualizza piano alimentare (read-only)."""
    plan = MealPlan.query.get_or_404(plan_id)
    
    # Verifica permessi (cliente può vedere il suo piano)
    if not current_user.is_admin:
        if hasattr(current_user, 'cliente_id'):
            if plan.cliente_id != current_user.cliente_id:
                abort(403)
        elif plan.created_by_id != current_user.id:
            abort(403)
    
    # Carica giorni con pasti
    days = MealPlanDay.query.filter_by(
        meal_plan_id=plan_id
    ).options(
        joinedload(MealPlanDay.meals).joinedload(Meal.foods)
    ).order_by(MealPlanDay.day_date).all()
    
    # Calcola totali
    plan_totals = {
        'calories': 0,
        'proteins': 0,
        'carbohydrates': 0,
        'fats': 0
    }
    
    for day in days:
        for meal in day.meals:
            plan_totals['calories'] += meal.total_calories
            plan_totals['proteins'] += meal.total_proteins
            plan_totals['carbohydrates'] += meal.total_carbohydrates
            plan_totals['fats'] += meal.total_fats
    
    # Media giornaliera
    if days:
        for key in plan_totals:
            plan_totals[key] = plan_totals[key] / len(days)
    
    return render_template('nutrition/meal_plans/view.html',
                         plan=plan,
                         days=days,
                         totals=plan_totals)


@bp.route('/meal-plans/<int:plan_id>/pdf')
@login_required
def meal_plan_pdf(plan_id):
    """Genera PDF del piano alimentare."""
    plan = MealPlan.query.get_or_404(plan_id)
    
    # Verifica permessi
    if not current_user.is_admin:
        if hasattr(current_user, 'cliente_id'):
            if plan.cliente_id != current_user.cliente_id:
                abort(403)
        elif plan.created_by_id != current_user.id:
            abort(403)
    
    try:
        pdf_path = create_meal_plan_pdf(plan)
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"piano_alimentare_{plan.cliente.nome_cognome}_{plan.start_date}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        current_app.logger.error(f"Errore generazione PDF: {str(e)}")
        flash('Errore nella generazione del PDF', 'danger')
        return redirect(url_for('nutrition.meal_plan_view', plan_id=plan_id))


# ===== DATABASE ALIMENTI =====
@bp.route('/foods')
@login_required
def food_database():
    """Database alimenti con ricerca."""
    search = request.args.get('search', '')
    category_id = request.args.get('category', type=int)
    page = request.args.get('page', 1, type=int)
    
    query = Food.query
    
    if search:
        query = query.filter(
            or_(
                Food.name.ilike(f'%{search}%'),
                Food.brand.ilike(f'%{search}%')
            )
        )
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    foods = query.order_by(Food.name).paginate(
        page=page, per_page=50, error_out=False
    )
    
    categories = FoodCategory.query.order_by(FoodCategory.name).all()
    
    return render_template('nutrition/foods/database.html',
                         foods=foods,
                         categories=categories,
                         search=search,
                         selected_category=category_id)


@bp.route('/foods/create', methods=['GET', 'POST'])
@login_required
def food_create():
    """Crea nuovo alimento."""
    if not current_user.is_admin and not current_user.is_nutritionist:
        abort(403)
    
    form = FoodForm()
    form.category_id.choices = [
        (c.id, c.name) for c in FoodCategory.query.order_by(FoodCategory.name).all()
    ]
    
    if form.validate_on_submit():
        food = Food()
        form.populate_obj(food)
        food.source = 'custom'
        food.verified = current_user.is_admin
        
        db.session.add(food)
        
        try:
            db.session.commit()
            flash('Alimento creato con successo', 'success')
            return redirect(url_for('nutrition.food_database'))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nel salvataggio: {str(e)}', 'danger')
    
    return render_template('nutrition/foods/create.html', form=form)


# ===== RICETTE =====
@bp.route('/recipes')
@login_required
def recipe_list():
    """Lista ricette."""
    search = request.args.get('search', '')
    filter_mine = request.args.get('mine', False, type=bool)
    page = request.args.get('page', 1, type=int)
    
    query = Recipe.query
    
    if search:
        query = query.filter(Recipe.name.ilike(f'%{search}%'))
    
    if filter_mine:
        query = query.filter_by(created_by_id=current_user.id)
    else:
        # Mostra ricette pubbliche + proprie
        query = query.filter(
            or_(
                Recipe.is_public == True,
                Recipe.created_by_id == current_user.id
            )
        )
    
    recipes = query.order_by(Recipe.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('nutrition/recipes/list.html',
                         recipes=recipes,
                         search=search,
                         filter_mine=filter_mine)


@bp.route('/recipes/create', methods=['GET', 'POST'])
@login_required
def recipe_create():
    """Crea nuova ricetta."""
    form = RecipeForm()
    
    if form.validate_on_submit():
        recipe = Recipe(
            name=form.name.data,
            description=form.description.data,
            preparation_time=form.preparation_time.data,
            cooking_time=form.cooking_time.data,
            servings=form.servings.data,
            difficulty=form.difficulty.data,
            instructions=form.instructions.data,
            notes=form.notes.data,
            tags=form.tags.data.split(',') if form.tags.data else [],
            is_public=form.is_public.data,
            created_by_id=current_user.id
        )
        
        db.session.add(recipe)
        
        try:
            db.session.commit()
            flash('Ricetta creata con successo. Ora aggiungi gli ingredienti.', 'success')
            return redirect(url_for('nutrition.recipe_view', recipe_id=recipe.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nel salvataggio: {str(e)}', 'danger')
    
    return render_template('nutrition/recipes/create.html', form=form)


@bp.route('/recipes/<int:recipe_id>')
@login_required
def recipe_view(recipe_id):
    """Visualizza ricetta con ingredienti."""
    recipe = Recipe.query.get_or_404(recipe_id)
    
    # Verifica permessi
    if not recipe.is_public and recipe.created_by_id != current_user.id:
        if not current_user.is_admin:
            abort(403)
    
    # Carica ingredienti con foods
    ingredients = RecipeIngredient.query.filter_by(
        recipe_id=recipe_id
    ).options(
        joinedload(RecipeIngredient.food)
    ).order_by(RecipeIngredient.order_index).all()
    
    # Calcola valori nutrizionali totali
    totals = {
        'calories': recipe.total_calories,
        'proteins': recipe.macros['proteins'],
        'carbohydrates': recipe.macros['carbohydrates'],
        'fats': recipe.macros['fats'],
        'fibers': recipe.macros['fibers']
    }
    
    # Per porzione
    per_serving = {k: v / recipe.servings for k, v in totals.items()} if recipe.servings > 0 else totals
    
    return render_template('nutrition/recipes/view.html',
                         recipe=recipe,
                         ingredients=ingredients,
                         totals=totals,
                         per_serving=per_serving)


# ===== TEMPLATE PIANI =====
@bp.route('/templates')
@login_required
def template_list():
    """Lista template piani alimentari."""
    templates = MealPlanTemplate.query.filter(
        or_(
            MealPlanTemplate.is_public == True,
            MealPlanTemplate.created_by_id == current_user.id
        )
    ).order_by(MealPlanTemplate.name).all()
    
    return render_template('nutrition/templates/list.html', templates=templates)


# ===== NOTE NUTRIZIONISTA =====
@bp.route('/clients/<int:cliente_id>/notes', methods=['POST'])
@login_required
def add_nutrition_note(cliente_id):
    """Aggiungi nota nutrizionale."""
    cliente = Cliente.query.get_or_404(cliente_id)
    
    # Verifica permessi
    if not current_user.is_admin:
        nutritionist_name = current_user.full_name.lower().replace(' ', '_')
        if not cliente.nutrizionista or nutritionist_name not in cliente.nutrizionista:
            abort(403)
    
    content = request.form.get('content', '').strip()
    is_private = request.form.get('is_private', type=bool, default=True)
    
    if content:
        note = NutritionNote(
            cliente_id=cliente_id,
            nutritionist_id=current_user.id,
            note_date=date.today(),
            content=content,
            is_private=is_private
        )
        db.session.add(note)
        
        try:
            db.session.commit()
            flash('Nota aggiunta con successo', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Errore nel salvataggio: {str(e)}', 'danger')
    
    return redirect(url_for('nutrition.client_profile', cliente_id=cliente_id))