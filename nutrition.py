import anthropic
import json
import re
import os

NUTRITION_SYSTEM = """You are a precise nutrition expert with deep knowledge of food composition databases (USDA FoodData Central, NUTTAB, McCance and Widdowson's).

When given a food item and quantity, provide comprehensive nutritional data based on established scientific databases. Use your knowledge of food composition to provide the most accurate estimates possible.

Always return ONLY a valid JSON object — no markdown, no explanation, just the JSON."""

NUTRITION_PROMPT = """Analyze the complete nutritional content of: {food}

Return ONLY this JSON structure with real numeric values (no nulls, use 0 if truly absent):

{{
  "food_name": "clear descriptive name of the food",
  "calories": 0,
  "macros": {{
    "protein_g": 0,
    "carbs_g": 0,
    "fat_g": 0,
    "fiber_g": 0,
    "sugar_g": 0,
    "net_carbs_g": 0
  }},
  "fats": {{
    "saturated_g": 0,
    "monounsaturated_g": 0,
    "polyunsaturated_g": 0,
    "trans_g": 0,
    "omega3_g": 0,
    "omega6_g": 0,
    "cholesterol_mg": 0
  }},
  "vitamins": {{
    "vitamin_a_mcg": 0,
    "vitamin_b1_mg": 0,
    "vitamin_b2_mg": 0,
    "vitamin_b3_mg": 0,
    "vitamin_b5_mg": 0,
    "vitamin_b6_mg": 0,
    "vitamin_b7_mcg": 0,
    "vitamin_b9_mcg": 0,
    "vitamin_b12_mcg": 0,
    "vitamin_c_mg": 0,
    "vitamin_d_mcg": 0,
    "vitamin_e_mg": 0,
    "vitamin_k_mcg": 0
  }},
  "minerals": {{
    "calcium_mg": 0,
    "iron_mg": 0,
    "magnesium_mg": 0,
    "phosphorus_mg": 0,
    "potassium_mg": 0,
    "sodium_mg": 0,
    "zinc_mg": 0,
    "copper_mg": 0,
    "manganese_mg": 0,
    "selenium_mcg": 0,
    "iodine_mcg": 0,
    "chromium_mcg": 0,
    "molybdenum_mcg": 0
  }},
  "amino_acids": {{
    "histidine_g": 0,
    "isoleucine_g": 0,
    "leucine_g": 0,
    "lysine_g": 0,
    "methionine_g": 0,
    "phenylalanine_g": 0,
    "threonine_g": 0,
    "tryptophan_g": 0,
    "valine_g": 0,
    "alanine_g": 0,
    "arginine_g": 0,
    "aspartic_acid_g": 0,
    "cysteine_g": 0,
    "glutamic_acid_g": 0,
    "glycine_g": 0,
    "proline_g": 0,
    "serine_g": 0,
    "tyrosine_g": 0
  }},
  "confidence": "high",
  "notes": "brief note about data source or any caveats"
}}"""


def analyze_food(food_description: str) -> dict:
    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    response = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=3000,
        system=NUTRITION_SYSTEM,
        messages=[{
            'role': 'user',
            'content': NUTRITION_PROMPT.format(food=food_description)
        }]
    )

    text = response.content[0].text.strip()

    # Strip markdown code blocks if present
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)

    # Extract JSON if wrapped in other text
    if not text.startswith('{'):
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            text = match.group()

    return json.loads(text)


def format_nutrition_summary(nd: dict) -> str:
    macros = nd.get('macros', {})
    fats = nd.get('fats', {})
    conf_emoji = {'high': '🟢', 'medium': '🟡', 'low': '🔴'}.get(nd.get('confidence', 'medium'), '🟡')

    lines = [
        f"*{nd.get('food_name', 'Food')}*",
        '',
        f"🔥 Calories: *{nd.get('calories', 0):.0f} kcal*",
        '',
        '*Macros:*',
        f"  💪 Protein: {macros.get('protein_g', 0):.1f}g",
        f"  🌾 Carbs: {macros.get('carbs_g', 0):.1f}g  (fiber: {macros.get('fiber_g', 0):.1f}g)",
        f"  🧈 Fat: {macros.get('fat_g', 0):.1f}g",
        '',
        '*Fats detail:*',
        f"  Saturated: {fats.get('saturated_g', 0):.2f}g  |  Omega-3: {fats.get('omega3_g', 0):.3f}g  |  Omega-6: {fats.get('omega6_g', 0):.3f}g",
        '',
        f"Confidence: {conf_emoji} {nd.get('confidence', 'medium').title()}",
    ]
    if nd.get('notes'):
        lines.append(f"_Note: {nd['notes']}_")
    return '\n'.join(lines)
