"""
Funzioni di utilità per il modulo Nutrition
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Tuple

from corposostenibile.models import (
    ActivityLevelEnum,
    GenereEnum,
    MealPlan,
    MealPlanDay,
    BiometricData,
    Food,
)

################################################################################
# Calcolo BMR, TDEE e macronutrienti
################################################################################


def calculate_bmr(weight: float, height: float, age: int, gender: GenereEnum) -> float:
    """
    Calcola il metabolismo basale (BMR) con la formula di Harris-Benedict rivista.
    """
    if gender == GenereEnum.uomo:
        bmr = 88.362 + 13.397 * weight + 4.799 * height - 5.677 * age
    else:
        bmr = 447.593 + 9.247 * weight + 3.098 * height - 4.330 * age
    return round(bmr, 2)


def calculate_tdee(bmr: float, activity_level: ActivityLevelEnum) -> float:
    """
    Calcola il Total Daily Energy Expenditure (TDEE).
    """
    multipliers: Dict[ActivityLevelEnum, float] = {
        ActivityLevelEnum.sedentario: 1.2,
        ActivityLevelEnum.leggermente_attivo: 1.375,
        ActivityLevelEnum.moderatamente_attivo: 1.55,
        ActivityLevelEnum.molto_attivo: 1.725,
        ActivityLevelEnum.estremamente_attivo: 1.9,
    }
    return round(bmr * multipliers.get(activity_level, 1.2), 2)


def calculate_macro_distribution(
    calories: float, goal: str = "mantenimento"
) -> Dict[str, float]:
    """
    Calcola la distribuzione dei macronutrienti (in grammi) partendo dalle calorie.
    """
    distributions: Dict[str, Dict[str, float]] = {
        "dimagrimento":   {"proteins_ratio": 0.30, "carbs_ratio": 0.35, "fats_ratio": 0.35},
        "mantenimento":   {"proteins_ratio": 0.25, "carbs_ratio": 0.45, "fats_ratio": 0.30},
        "aumento_massa":  {"proteins_ratio": 0.25, "carbs_ratio": 0.50, "fats_ratio": 0.25},
        "ricomposizione": {"proteins_ratio": 0.35, "carbs_ratio": 0.35, "fats_ratio": 0.30},
        "salute_generale": {"proteins_ratio": 0.20, "carbs_ratio": 0.50, "fats_ratio": 0.30},
    }
    ratios = distributions.get(goal, distributions["mantenimento"])

    protein_kcal = calories * ratios["proteins_ratio"]
    carb_kcal = calories * ratios["carbs_ratio"]
    fat_kcal = calories * ratios["fats_ratio"]

    return {
        "proteins": round(protein_kcal / 4, 1),
        "carbohydrates": round(carb_kcal / 4, 1),
        "fats": round(fat_kcal / 9, 1),
    }

################################################################################
# BMI, peso ideale e composizione corporea
################################################################################


def calculate_bmi(weight: float, height: float) -> Tuple[float, str]:
    """
    Calcola BMI e categoria associata.
    """
    bmi = weight / ((height / 100) ** 2)

    if bmi < 18.5:
        category = "Sottopeso"
    elif bmi < 25:
        category = "Normopeso"
    elif bmi < 30:
        category = "Sovrappeso"
    elif bmi < 35:
        category = "Obesità I grado"
    elif bmi < 40:
        category = "Obesità II grado"
    else:
        category = "Obesità III grado"

    return round(bmi, 1), category


def calculate_ideal_weight(height: float, gender: GenereEnum) -> Tuple[float, float]:
    """
    Calcola il peso ideale (formula di Lorenz) restituendo il range ±10 %.
    """
    if gender == GenereEnum.uomo:
        ideal = height - 100 - (height - 150) / 4
    else:
        ideal = height - 100 - (height - 150) / 2

    return round(ideal * 0.9, 1), round(ideal * 1.1, 1)


def analyze_body_composition(biometric: BiometricData) -> Dict[str, Any]:
    """
    Analizza i dati biometrici e restituisce una valutazione completa.
    """
    analysis: Dict[str, Any] = {
        "bmi": None,
        "bmi_category": None,
        "waist_hip_ratio": None,
        "whr_risk": None,
        "body_fat_category": None,
        "muscle_mass_category": None,
        "hydration_status": None,
        "recommendations": [],
    }

    # BMI
    if biometric.weight and biometric.height:
        analysis["bmi"], analysis["bmi_category"] = calculate_bmi(
            biometric.weight, biometric.height
        )

    # Rapporto vita/fianchi
    if biometric.waist and biometric.hips:
        whr = biometric.waist / biometric.hips
        analysis["waist_hip_ratio"] = round(whr, 2)

        gender = getattr(
            getattr(biometric, "cliente", None), "nutritional_profile", None
        )
        gender = getattr(gender, "gender", None)

        if gender == GenereEnum.uomo:
            analysis["whr_risk"] = (
                "Alto" if whr > 0.95 else "Moderato" if whr > 0.90 else "Basso"
            )
        elif gender == GenereEnum.donna:
            analysis["whr_risk"] = (
                "Alto" if whr > 0.85 else "Moderato" if whr > 0.80 else "Basso"
            )

    # Massa grassa
    if biometric.body_fat_percentage is not None:
        bf = biometric.body_fat_percentage
        gender = getattr(
            getattr(biometric, "cliente", None), "nutritional_profile", None
        )
        gender = getattr(gender, "gender", None)

        if gender == GenereEnum.uomo:
            if bf < 6:
                cat = "Essenziale"
            elif bf < 14:
                cat = "Atletico"
            elif bf < 18:
                cat = "Fitness"
            elif bf < 25:
                cat = "Accettabile"
            else:
                cat = "Obesità"
        elif gender == GenereEnum.donna:
            if bf < 14:
                cat = "Essenziale"
            elif bf < 21:
                cat = "Atletico"
            elif bf < 25:
                cat = "Fitness"
            elif bf < 32:
                cat = "Accettabile"
            else:
                cat = "Obesità"
        else:
            cat = None

        analysis["body_fat_category"] = cat

    # Idratazione
    if biometric.water_percentage is not None:
        water = biometric.water_percentage
        if water < 45:
            analysis["hydration_status"] = "Disidratazione severa"
            analysis["recommendations"].append(
                "Aumentare urgentemente l'assunzione di acqua."
            )
        elif water < 50:
            analysis["hydration_status"] = "Disidratazione lieve"
            analysis["recommendations"].append("Incrementare l'idratazione giornaliera.")
        elif water < 65:
            analysis["hydration_status"] = "Normale"
        else:
            analysis["hydration_status"] = "Ottimale"

    return analysis

################################################################################
# Validazione date piano alimentare
################################################################################


def validate_meal_plan_dates(start_date: date, end_date: date) -> bool:
    """
    Valida che l'intervallo di date del piano alimentare sia corretto (max 90 giorni).
    """
    if start_date >= end_date:
        return False
    return (end_date - start_date).days <= 90

################################################################################
# Lista della spesa
################################################################################


def _add_food_to_shopping_list(
    shopping_list: Dict[str, Dict[str, Any]],
    food: Food,
    quantity: float,
) -> None:
    """
    Helper per inserire/aggiornare un alimento nella lista della spesa.
    """
    category = food.category.name if food.category else "Altro"
    key = f"{food.name} {food.brand or ''}".strip()

    if category not in shopping_list:
        shopping_list[category] = {}

    if key not in shopping_list[category]:
        shopping_list[category][key] = {
            "quantity": 0.0,
            "unit": "g",
            "food_id": food.id,
        }

    shopping_list[category][key]["quantity"] += quantity


def calculate_shopping_list(meal_plan: MealPlan) -> Dict[str, Dict[str, Any]]:
    """
    Aggrega gli alimenti di un MealPlan restituendo una lista della spesa.
    """
    shopping_list: Dict[str, Dict[str, Any]] = {}
    days = MealPlanDay.query.filter_by(meal_plan_id=meal_plan.id).all()

    for day in days:
        for meal in day.meals:
            for meal_food in meal.foods:
                if meal_food.food:
                    _add_food_to_shopping_list(
                        shopping_list, meal_food.food, meal_food.grams
                    )
                elif meal_food.recipe:
                    for ing in meal_food.recipe.ingredients:
                        qty = ing.grams * meal_food.quantity
                        _add_food_to_shopping_list(shopping_list, ing.food, qty)

    # Arrotonda le quantità
    for cat in shopping_list.values():
        for item in cat.values():
            item["quantity"] = round(item["quantity"], 0)

    return shopping_list

################################################################################
# PDF del piano alimentare
################################################################################


def generate_meal_plan_pdf(meal_plan: MealPlan) -> str:
    """
    Genera un PDF del piano alimentare e restituisce il path del file.
    """
    from .pdf import create_meal_plan_pdf

    return create_meal_plan_pdf(meal_plan)

################################################################################
# Suggerimenti di alimenti alternativi
################################################################################


def suggest_food_alternatives(
    food_id: int,
    dietary_preferences: List[str] | None = None,
    intolerances: List[str] | None = None,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Suggerisce alimenti alternativi con profilo nutrizionale simile.
    """
    original = Food.query.get(food_id)
    if original is None:
        return []

    query = Food.query.filter(
        Food.id != food_id,
        Food.category_id == original.category_id,
    )

    # TODO: filtri su dietary_preferences o intolerances

    candidates = query.limit(limit * 3).all()
    scored: List[Tuple[float, Food]] = []

    for alt in candidates:
        cal_diff = abs(alt.calories - original.calories)
        prot_diff = abs(alt.proteins - original.proteins)
        score = cal_diff + prot_diff * 4  # Peso maggiore alle proteine
        scored.append((score, alt))

    scored.sort(key=lambda x: x[0])

    suggestions: List[Dict[str, Any]] = []
    for _, alt in scored[:limit]:
        suggestions.append(
            {
                "id": alt.id,
                "name": alt.name,
                "brand": alt.brand,
                "calories": alt.calories,
                "proteins": alt.proteins,
                "cal_diff": abs(alt.calories - original.calories),
                "prot_diff": abs(alt.proteins - original.proteins),
            }
        )

    return suggestions

################################################################################
# Verifica compliance nutrizionale
################################################################################


def check_nutritional_compliance(
    meal_plan: MealPlan, tolerance: float = 0.10
) -> Dict[str, Any]:
    """
    Verifica la conformità del piano alimentare rispetto ai target con una
    tolleranza percentuale (default 10 %).
    """
    days = MealPlanDay.query.filter_by(meal_plan_id=meal_plan.id).all()
    if not days:
        return {"compliant": False, "message": "Nessun giorno nel piano"}

    daily_totals: List[Dict[str, float]] = []
    for day in days:
        totals = {"calories": 0.0, "proteins": 0.0, "carbohydrates": 0.0, "fats": 0.0}
        for meal in day.meals:
            totals["calories"] += meal.total_calories
            totals["proteins"] += meal.total_proteins
            totals["carbohydrates"] += meal.total_carbohydrates
            totals["fats"] += meal.total_fats
        daily_totals.append(totals)

    avg = {
        macro: sum(d[macro] for d in daily_totals) / len(daily_totals)
        for macro in ("calories", "proteins", "carbohydrates", "fats")
    }

    compliance = {
        "compliant": True,
        "averages": avg,
        "targets": {
            "calories": meal_plan.target_calories,
            "proteins": meal_plan.target_proteins,
            "carbohydrates": meal_plan.target_carbohydrates,
            "fats": meal_plan.target_fats,
        },
        "deviations": {},
    }

    for macro, target in compliance["targets"].items():
        if target is None or target <= 0:
            continue
        actual = avg[macro]
        deviation_pct = (actual - target) / target * 100
        compliance["deviations"][macro] = {
            "percentage": round(deviation_pct, 1),
            "absolute": round(actual - target, 1),
            "within_tolerance": abs(deviation_pct) <= tolerance * 100,
        }
        if not compliance["deviations"][macro]["within_tolerance"]:
            compliance["compliant"] = False

    return compliance
