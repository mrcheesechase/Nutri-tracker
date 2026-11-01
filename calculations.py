from datetime import date, timedelta

ACTIVITY_MULTIPLIERS = {
    'sedentary': 1.2,
    'light': 1.375,
    'moderate': 1.55,
    'active': 1.725,
    'very_active': 1.9,
}

ACTIVITY_LABELS = {
    'sedentary': 'Sedentary (desk job, little/no exercise)',
    'light': 'Lightly Active (1-3 days/week)',
    'moderate': 'Moderately Active (3-5 days/week)',
    'active': 'Very Active (6-7 days/week)',
    'very_active': 'Extra Active (physical job + hard training)',
}


def calculate_bmr(weight_kg, height_cm, age, gender):
    if gender.lower() == 'male':
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


def calculate_tdee(bmr, activity_level):
    return bmr * ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)


def calculate_daily_calorie_target(tdee, start_weight, goal_weight, weeks):
    weight_to_lose = start_weight - goal_weight
    if weight_to_lose <= 0:
        return tdee + 300  # surplus for gaining

    total_deficit = weight_to_lose * 7700
    daily_deficit = total_deficit / (weeks * 7)
    daily_deficit = min(daily_deficit, 1000)  # safety cap
    target = tdee - daily_deficit
    return max(target, 1200)  # never below 1200


def calculate_macros(calorie_target, weight_kg):
    protein_g = round(weight_kg * 2.0, 1)  # 2g/kg body weight
    protein_cal = protein_g * 4
    fat_cal = calorie_target * 0.28
    fat_g = round(fat_cal / 9, 1)
    remaining = calorie_target - protein_cal - fat_cal
    carb_g = round(max(remaining / 4, 50), 1)
    return {'protein_g': protein_g, 'fat_g': fat_g, 'carbs_g': carb_g}


def get_goal_date(created_at_str, goal_weeks):
    created = date.fromisoformat(created_at_str[:10])
    return created + timedelta(weeks=goal_weeks)


def get_rda(age, gender, weight_kg):
    m = gender.lower() == 'male'
    return {
        'vitamins': {
            'vitamin_a_mcg': 900 if m else 700,
            'vitamin_b1_mg': 1.2 if m else 1.1,
            'vitamin_b2_mg': 1.3 if m else 1.1,
            'vitamin_b3_mg': 16 if m else 14,
            'vitamin_b5_mg': 5.0,
            'vitamin_b6_mg': 1.7 if age >= 51 else 1.3,
            'vitamin_b7_mcg': 30.0,
            'vitamin_b9_mcg': 400.0,
            'vitamin_b12_mcg': 2.4,
            'vitamin_c_mg': 90 if m else 75,
            'vitamin_d_mcg': 20 if age >= 70 else 15,
            'vitamin_e_mg': 15.0,
            'vitamin_k_mcg': 120 if m else 90,
        },
        'minerals': {
            'calcium_mg': 1200 if age >= 51 else 1000,
            'iron_mg': 8 if m or age >= 51 else 18,
            'magnesium_mg': 420 if m else 320,
            'phosphorus_mg': 700.0,
            'potassium_mg': 3400 if m else 2600,
            'sodium_mg': 2300.0,
            'zinc_mg': 11 if m else 8,
            'copper_mg': 0.9,
            'manganese_mg': 2.3 if m else 1.8,
            'selenium_mcg': 55.0,
            'iodine_mcg': 150.0,
            'chromium_mcg': 35 if m else 25,
            'molybdenum_mcg': 45.0,
        },
        'amino_acids': {
            'histidine_g': round(weight_kg * 0.014, 2),
            'isoleucine_g': round(weight_kg * 0.019, 2),
            'leucine_g': round(weight_kg * 0.042, 2),
            'lysine_g': round(weight_kg * 0.038, 2),
            'methionine_g': round(weight_kg * 0.019, 2),
            'phenylalanine_g': round(weight_kg * 0.033, 2),
            'threonine_g': round(weight_kg * 0.020, 2),
            'tryptophan_g': round(weight_kg * 0.005, 2),
            'valine_g': round(weight_kg * 0.024, 2),
        },
    }


def weight_progress_stats(user, weight_logs):
    if not weight_logs:
        return None
    current = weight_logs[0]['weight_kg']
    start = user['start_weight_kg']
    goal = user['goal_weight_kg']
    lost = start - current
    remaining = current - goal
    pct = (lost / (start - goal) * 100) if start != goal else 0
    return {
        'current': current,
        'start': start,
        'goal': goal,
        'lost': lost,
        'remaining': remaining,
        'pct': pct,
    }
