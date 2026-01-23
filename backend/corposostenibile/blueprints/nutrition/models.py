"""
Import dei modelli nutrition per comodità
"""

from corposostenibile.models import (
    # Enums
    MealTypeEnum,
    DietaryPreferenceEnum,
    NutritionalGoalEnum,
    ActivityLevelEnum,
    FoodUnitEnum,
    
    # Modelli alimenti
    Food,
    FoodCategory,
    Recipe,
    RecipeIngredient,
    
    # Modelli piani
    MealPlan,
    MealPlanDay,
    Meal,
    MealFood,
    MealPlanTemplate,
    
    # Modelli cliente
    NutritionalProfile,
    HealthAssessment,
    BiometricData,
    DietaryPreference,
    FoodIntolerance,
    NutritionNote
)

__all__ = [
    'MealTypeEnum',
    'DietaryPreferenceEnum',
    'NutritionalGoalEnum',
    'ActivityLevelEnum',
    'FoodUnitEnum',
    'Food',
    'FoodCategory',
    'Recipe',
    'RecipeIngredient',
    'MealPlan',
    'MealPlanDay',
    'Meal',
    'MealFood',
    'MealPlanTemplate',
    'NutritionalProfile',
    'HealthAssessment',
    'BiometricData',
    'DietaryPreference',
    'FoodIntolerance',
    'NutritionNote'
]