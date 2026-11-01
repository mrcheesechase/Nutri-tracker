"""
Weight Loss & Nutrition Tracker — Telegram Bot
Run: python bot.py
Requires: ANTHROPIC_API_KEY environment variable
"""
import logging
import os
import re
import warnings
from datetime import date, timedelta
from pathlib import Path

warnings.filterwarnings('ignore', message='.*per_message.*')

from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    CallbackQueryHandler, filters, ContextTypes,
)

import database as db
import calculations as calc
import nutrition as nutr
import graphs

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# ── Conversation states ──────────────────────────────────────────────────────
(
    ONB_NAME, ONB_AGE, ONB_GENDER, ONB_HEIGHT, ONB_WEIGHT,
    ONB_GOAL_WEIGHT, ONB_ACTIVITY, ONB_GOAL_WEEKS,
    W_VALUE,
    F_MEAL, F_DESC, F_CONFIRM,
    PH_RECEIVE, PH_CAPTION,
    RESET_CONFIRM,
) = range(15)

# ── UI helpers ───────────────────────────────────────────────────────────────
ACTIVITY_KEYS = {
    '🪑 Sedentary (desk job, little exercise)': 'sedentary',
    '🚶 Lightly Active (1-3 days/week)': 'light',
    '🏃 Moderately Active (3-5 days/week)': 'moderate',
    '💪 Very Active (6-7 days/week)': 'active',
    '🔥 Extra Active (hard job + intense training)': 'very_active',
}

MEALS = ['🌅 Breakfast', '☀️ Lunch', '🌙 Dinner', '🍎 Snack', '💊 Supplement', '🥤 Drink']

MAIN_KB = ReplyKeyboardMarkup([
    ['⚖️ Log Weight', '🍽️ Log Food'],
    ['📊 Today\'s Summary', '📈 Progress Graph'],
    ['🔬 Nutrients', '📸 Progress Photos'],
    ['👤 My Profile', '🎯 My Goals'],
], resize_keyboard=True)


def parse_weight(text):
    """Return kg float from text like '80.5', '80.5 kg', '177 lbs'."""
    text = text.strip().lower()
    if 'lb' in text:
        num = float(re.sub(r'[^\d.]', '', text))
        return num * 0.453592
    num = float(re.sub(r'[^\d.]', '', text))
    return num


def parse_height(text):
    """Return cm float from '175', '175cm', '5\'10\"', '5 10'."""
    text = text.strip()
    # feet'inches or feet inches
    m = re.match(r"(\d+)['\s](\d+)", text)
    if m:
        return int(m.group(1)) * 30.48 + int(m.group(2)) * 2.54
    # plain number (assume cm)
    return float(re.sub(r'[^\d.]', '', text))


def pbar(pct, width=10):
    filled = int(min(pct / 100, 1.0) * width)
    return '█' * filled + '░' * (width - filled)


def traffic(pct):
    if pct >= 80:
        return '✅'
    elif pct >= 50:
        return '🟡'
    return '🔴'


# ── /start & onboarding ──────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db.get_user(uid)
    if user:
        await update.message.reply_text(
            f"Welcome back, *{user['name']}*! 👋",
            parse_mode='Markdown',
            reply_markup=MAIN_KB
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "👋 *Welcome to your Weight Loss & Nutrition Tracker!*\n\n"
        "I'll help you track your weight, food intake, and nutrition to reach your goals.\n\n"
        "Let's set up your profile first.\n\n"
        "What's your *name*?",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )
    return ONB_NAME


async def onb_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if len(name) < 1 or len(name) > 50:
        await update.message.reply_text("Please enter a valid name:")
        return ONB_NAME
    ctx.user_data['name'] = name
    await update.message.reply_text(
        f"Great, {name}! 🎉\n\nHow old are you? *(enter a number, e.g. 28)*",
        parse_mode='Markdown'
    )
    return ONB_AGE


async def onb_age(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text.strip())
        assert 10 <= age <= 120
    except Exception:
        await update.message.reply_text("Please enter a valid age (e.g. 28):")
        return ONB_AGE
    ctx.user_data['age'] = age
    kb = ReplyKeyboardMarkup([['Male', 'Female']], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("What's your *gender*?", parse_mode='Markdown', reply_markup=kb)
    return ONB_GENDER


async def onb_gender(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    g = update.message.text.strip().lower()
    if g not in ('male', 'female'):
        kb = ReplyKeyboardMarkup([['Male', 'Female']], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Please choose Male or Female:", reply_markup=kb)
        return ONB_GENDER
    ctx.user_data['gender'] = g
    await update.message.reply_text(
        "📏 What's your *height*?\n\n"
        "You can enter:\n• cm: `175`\n• feet/inches: `5'10\"` or `5 10`",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )
    return ONB_HEIGHT


async def onb_height(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        h = parse_height(update.message.text)
        assert 100 <= h <= 250
    except Exception:
        await update.message.reply_text("Please enter a valid height (e.g. 175 or 5'10\"):")
        return ONB_HEIGHT
    ctx.user_data['height_cm'] = h
    await update.message.reply_text(
        f"Height recorded: *{h:.1f} cm* ✓\n\n"
        "⚖️ What's your *current weight*?\n\nYou can use kg or lbs (e.g. `82.5` or `180 lbs`)",
        parse_mode='Markdown'
    )
    return ONB_WEIGHT


async def onb_weight(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        w = parse_weight(update.message.text)
        assert 20 <= w <= 500
    except Exception:
        await update.message.reply_text("Please enter a valid weight (e.g. 82.5 or 180 lbs):")
        return ONB_WEIGHT
    ctx.user_data['start_weight_kg'] = w
    await update.message.reply_text(
        f"Current weight: *{w:.1f} kg* ✓\n\n"
        "🎯 What's your *goal weight*?",
        parse_mode='Markdown'
    )
    return ONB_GOAL_WEIGHT


async def onb_goal_weight(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        w = parse_weight(update.message.text)
        assert 20 <= w <= 500
    except Exception:
        await update.message.reply_text("Please enter a valid goal weight:")
        return ONB_GOAL_WEIGHT
    ctx.user_data['goal_weight_kg'] = w
    kb = ReplyKeyboardMarkup([[k] for k in ACTIVITY_KEYS], one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        f"Goal weight: *{w:.1f} kg* ✓\n\n"
        "🏃 What's your *activity level*?",
        parse_mode='Markdown',
        reply_markup=kb
    )
    return ONB_ACTIVITY


async def onb_activity(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sel = update.message.text.strip()
    if sel not in ACTIVITY_KEYS:
        kb = ReplyKeyboardMarkup([[k] for k in ACTIVITY_KEYS], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Please select an activity level:", reply_markup=kb)
        return ONB_ACTIVITY
    ctx.user_data['activity_level'] = ACTIVITY_KEYS[sel]
    await update.message.reply_text(
        "📅 In *how many weeks* do you want to reach your goal?\n\n"
        "E.g. `12` for 3 months, `24` for 6 months.",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )
    return ONB_GOAL_WEEKS


async def onb_goal_weeks(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        weeks = int(update.message.text.strip())
        assert 1 <= weeks <= 520
    except Exception:
        await update.message.reply_text("Please enter a number of weeks (e.g. 12):")
        return ONB_GOAL_WEEKS

    d = ctx.user_data
    bmr = calc.calculate_bmr(d['start_weight_kg'], d['height_cm'], d['age'], d['gender'])
    tdee = calc.calculate_tdee(bmr, d['activity_level'])
    cal_target = calc.calculate_daily_calorie_target(tdee, d['start_weight_kg'], d['goal_weight_kg'], weeks)
    macros = calc.calculate_macros(cal_target, d['start_weight_kg'])

    user_data = {
        'user_id': update.effective_user.id,
        'name': d['name'], 'age': d['age'], 'gender': d['gender'],
        'height_cm': d['height_cm'], 'start_weight_kg': d['start_weight_kg'],
        'goal_weight_kg': d['goal_weight_kg'], 'activity_level': d['activity_level'],
        'goal_weeks': weeks, 'bmr': bmr, 'tdee': tdee,
        'daily_calorie_target': cal_target,
        'protein_target_g': macros['protein_g'],
        'fat_target_g': macros['fat_g'],
        'carb_target_g': macros['carbs_g'],
    }
    db.save_user(user_data)

    diff = d['start_weight_kg'] - d['goal_weight_kg']
    goal_date = (date.today() + timedelta(weeks=weeks)).strftime('%B %d, %Y')
    deficit = tdee - cal_target

    await update.message.reply_text(
        f"✅ *Profile Created!*\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Your Metabolic Stats:*\n"
        f"• BMR: {bmr:.0f} kcal/day\n"
        f"• TDEE: {tdee:.0f} kcal/day\n"
        f"• Daily deficit: {deficit:.0f} kcal\n\n"
        f"🎯 *Daily Targets:*\n"
        f"• 🔥 Calories: *{cal_target:.0f} kcal*\n"
        f"• 💪 Protein: {macros['protein_g']:.0f}g\n"
        f"• 🧈 Fat: {macros['fat_g']:.0f}g\n"
        f"• 🌾 Carbs: {macros['carbs_g']:.0f}g\n\n"
        f"📅 *Goal:*\n"
        f"• Lose *{max(diff,0):.1f} kg* in *{weeks} weeks*\n"
        f"• Target date: {goal_date}\n"
        f"• Approx ~{max(diff,0)/weeks:.2f} kg/week\n\n"
        f"Let's get started! 💪",
        parse_mode='Markdown',
        reply_markup=MAIN_KB
    )
    ctx.user_data.clear()
    return ConversationHandler.END


# ── Weight logging ───────────────────────────────────────────────────────────
async def log_weight_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not db.get_user(uid):
        await update.message.reply_text("Please set up your profile first with /start")
        return ConversationHandler.END
    await update.message.reply_text(
        "⚖️ *Log Today's Weight*\n\nEnter your weight (kg or lbs):",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )
    return W_VALUE


async def log_weight_value(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        w = parse_weight(update.message.text)
        assert 20 <= w <= 500
    except Exception:
        await update.message.reply_text("Invalid weight. Please try again (e.g. 79.5 or 175 lbs):")
        return W_VALUE

    uid = update.effective_user.id
    db.log_weight(uid, w)
    user = db.get_user(uid)
    logs = db.get_weight_logs(uid, 2)

    lost = user['start_weight_kg'] - w
    remaining = w - user['goal_weight_kg']
    delta_str = ''
    if len(logs) >= 2:
        prev = logs[1]['weight_kg']
        delta = w - prev
        delta_str = f"\n• vs yesterday: {'▲' if delta > 0 else '▼'} {abs(delta):.2f} kg"

    await update.message.reply_text(
        f"✅ Weight logged: *{w:.1f} kg*\n\n"
        f"• Lost so far: {max(lost,0):.1f} kg\n"
        f"• Remaining: {max(remaining,0):.1f} kg{delta_str}\n\n"
        f"{'🎉 You reached your goal! Amazing!' if remaining <= 0 else ''}",
        parse_mode='Markdown',
        reply_markup=MAIN_KB
    )
    return ConversationHandler.END


# ── Food logging ─────────────────────────────────────────────────────────────
async def log_food_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not db.get_user(uid):
        if update.message:
            await update.message.reply_text("Please set up your profile first with /start")
        return ConversationHandler.END

    kb = ReplyKeyboardMarkup([[m] for m in MEALS], one_time_keyboard=True, resize_keyboard=True)
    target = update.message or update.callback_query.message
    await target.reply_text("🍽️ *Log Food*\n\nSelect meal type:", parse_mode='Markdown', reply_markup=kb)
    return F_MEAL


async def food_meal(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    sel = update.message.text.strip()
    if sel not in MEALS:
        kb = ReplyKeyboardMarkup([[m] for m in MEALS], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Please select a meal type:", reply_markup=kb)
        return F_MEAL
    ctx.user_data['meal_type'] = sel.split(' ', 1)[-1]
    await update.message.reply_text(
        "📝 Describe what you ate *including the amount*:\n\n"
        "Examples:\n"
        "• `2 scrambled eggs with 1 tbsp butter`\n"
        "• `150g grilled chicken breast`\n"
        "• `1 cup oatmeal with banana and 1 tsp honey`\n"
        "• `McDonald's Big Mac and medium fries`\n"
        "• `1 glass whole milk (250ml)`",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )
    return F_DESC


async def food_desc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    food_text = update.message.text.strip()
    ctx.user_data['food_text'] = food_text

    wait_msg = await update.message.reply_text("🔍 Analyzing nutrition with AI… (a few seconds)")

    if not os.environ.get('ANTHROPIC_API_KEY'):
        await wait_msg.delete()
        await update.message.reply_text(
            "⚠️ *ANTHROPIC_API_KEY not configured!*\n\n"
            "To enable AI nutrition analysis:\n\n"
            "1. Get a free API key at:\n   `console.anthropic.com/settings/keys`\n\n"
            "2. Create a `.env` file in the project folder:\n"
            "   `ANTHROPIC_API_KEY=sk-ant-api03-...`\n\n"
            "3. Restart the bot\n\n"
            "_You can also log food manually without analysis for now._",
            parse_mode='Markdown',
            reply_markup=MAIN_KB
        )
        return ConversationHandler.END

    try:
        nd = nutr.analyze_food(food_text)
        ctx.user_data['nd'] = nd
        await wait_msg.delete()

        summary = nutr.format_nutrition_summary(nd)
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Save", callback_data='food_save'),
            InlineKeyboardButton("❌ Cancel", callback_data='food_cancel'),
        ]])
        await update.message.reply_text(
            summary + "\n\n*Save this entry?*",
            parse_mode='Markdown',
            reply_markup=kb
        )
        return F_CONFIRM
    except Exception as e:
        logger.error(f"Nutrition error: {e}")
        await wait_msg.delete()
        await update.message.reply_text(
            "❌ Could not analyze that food. Please try a clearer description.",
            reply_markup=MAIN_KB
        )
        return ConversationHandler.END


async def food_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'food_save':
        uid = update.effective_user.id
        db.log_food(
            uid,
            ctx.user_data.get('meal_type', 'Snack'),
            ctx.user_data.get('food_text', ''),
            ctx.user_data.get('food_text', ''),
            ctx.user_data.get('nd', {}),
        )
        await query.edit_message_text(
            query.message.text_markdown_v2_urled or query.message.text,
            parse_mode='Markdown'
        )
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("➕ Log More Food", callback_data='log_more_food'),
            InlineKeyboardButton("📊 View Today", callback_data='view_today'),
        ]])
        await query.message.reply_text("✅ *Saved!* What's next?", parse_mode='Markdown', reply_markup=kb)
    else:
        await query.edit_message_text("❌ Cancelled.")
        await query.message.reply_text("No problem!", reply_markup=MAIN_KB)

    for k in ('meal_type', 'food_text', 'nd'):
        ctx.user_data.pop(k, None)
    return ConversationHandler.END


# ── Photo upload ─────────────────────────────────────────────────────────────
async def photo_upload_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "📸 *Send your progress photo now!*\n\nYou can include a caption — just add it to the photo message.",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )
    return PH_RECEIVE


async def photo_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Please send a photo.")
        return PH_RECEIVE
    photo = update.message.photo[-1]
    caption = update.message.caption or ''
    db.save_progress_photo(update.effective_user.id, photo.file_id, caption)
    today = date.today().strftime('%B %d, %Y')
    await update.message.reply_text(
        f"✅ Progress photo saved for *{today}*!",
        parse_mode='Markdown',
        reply_markup=MAIN_KB
    )
    return ConversationHandler.END


# ── Summaries & graphs ───────────────────────────────────────────────────────
async def today_summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db.get_user(uid)
    if not user:
        await update.message.reply_text("No profile found. Use /start to set up.")
        return

    logs = db.get_food_logs_date(uid)
    today_weight = db.get_today_weight(uid)

    if not logs:
        w_str = f"\n⚖️ Weight today: {today_weight:.1f} kg\n" if today_weight else ""
        await update.message.reply_text(
            f"📋 *Today — {date.today().strftime('%B %d, %Y')}*\n"
            f"{w_str}\n"
            f"No food logged yet!\nUse *🍽️ Log Food* to start tracking.",
            parse_mode='Markdown'
        )
        return

    cal = sum(l['calories'] or 0 for l in logs)
    pro = sum(l['protein_g'] or 0 for l in logs)
    fat = sum(l['fat_g'] or 0 for l in logs)
    carb = sum(l['carbs_g'] or 0 for l in logs)
    fiber = sum(l['fiber_g'] or 0 for l in logs)
    omega3 = sum(l['omega3_g'] or 0 for l in logs)

    t_cal = user['daily_calorie_target']
    t_pro = user['protein_target_g']
    t_fat = user['fat_target_g']
    t_carb = user['carb_target_g']

    def row(label, actual, target, unit='g'):
        pct = actual / target * 100 if target else 0
        return f"{traffic(pct)} *{label}:* {actual:.0f}{unit} / {target:.0f}{unit}  `{pbar(pct)}`  {pct:.0f}%"

    w_str = f"⚖️ Weight today: *{today_weight:.1f} kg*\n\n" if today_weight else ""

    # Build food list grouped by meal
    meal_lines = {}
    for l in logs:
        meal = l['meal_type']
        meal_lines.setdefault(meal, []).append(f"  • {l['food_description'][:45]}  _({l['calories']:.0f} kcal)_")
    food_str = ''
    for meal, items in meal_lines.items():
        food_str += f"\n*{meal}:*\n" + '\n'.join(items) + '\n'

    text = (
        f"📋 *Today — {date.today().strftime('%B %d, %Y')}*\n\n"
        f"{w_str}"
        f"{row('Calories', cal, t_cal, ' kcal')}\n"
        f"{row('Protein', pro, t_pro)}\n"
        f"{row('Fat', fat, t_fat)}\n"
        f"{row('Carbs', carb, t_carb)}\n\n"
        f"🥗 Fiber: {fiber:.1f}g  |  🐟 Omega-3: {omega3:.3f}g\n"
        f"\n📝 *Foods logged:*{food_str}"
    )

    chart = graphs.nutrition_summary_chart(logs, user)
    if chart:
        await update.message.reply_photo(photo=chart, caption=text, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, parse_mode='Markdown')


async def progress_graph(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db.get_user(uid)
    if not user:
        await update.message.reply_text("No profile found. Use /start to set up.")
        return

    logs = db.get_weight_logs(uid, 90)
    if not logs:
        await update.message.reply_text(
            "📈 No weight data yet!\n\nUse *⚖️ Log Weight* to start tracking.",
            parse_mode='Markdown'
        )
        return

    chart = graphs.weight_progress_chart(logs, user)
    stats = calc.weight_progress_stats(user, logs)
    goal_date = calc.get_goal_date(user['created_at'], user['goal_weeks'])

    caption = (
        f"📈 *Weight Progress*\n\n"
        f"• Start: {stats['start']:.1f} kg\n"
        f"• Current: {stats['current']:.1f} kg\n"
        f"• Lost: {max(stats['lost'],0):.1f} kg\n"
        f"• Remaining: {max(stats['remaining'],0):.1f} kg\n"
        f"• Progress: {max(stats['pct'],0):.1f}%\n"
        f"• Goal date: {goal_date.strftime('%B %d, %Y')}\n"
        f"• Entries: {len(logs)}"
    )

    if chart:
        await update.message.reply_photo(photo=chart, caption=caption, parse_mode='Markdown')
    else:
        await update.message.reply_text(caption, parse_mode='Markdown')


async def nutrients_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    logs = db.get_food_logs_date(uid)
    if not logs:
        await update.message.reply_text(
            "🔬 No food logged today.\n\nLog some food first to see your micronutrients!"
        )
        return
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("💊 Vitamins", callback_data='nutr_vitamins'),
        InlineKeyboardButton("⛏️ Minerals", callback_data='nutr_minerals'),
    ], [
        InlineKeyboardButton("🥩 Amino Acids", callback_data='nutr_amino_acids'),
        InlineKeyboardButton("📅 Calorie History", callback_data='nutr_cal_history'),
    ]])
    await update.message.reply_text(
        "🔬 *Micronutrient Analysis*\n\nSelect a report to view:",
        parse_mode='Markdown',
        reply_markup=kb
    )


async def nutrients_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    user = db.get_user(uid)
    if not user:
        await query.message.reply_text("No profile found.")
        return

    chart_type = query.data.replace('nutr_', '')

    if chart_type == 'cal_history':
        from datetime import datetime
        end = date.today().isoformat()
        start = (date.today() - timedelta(days=13)).isoformat()
        daily = db.get_food_logs_range(uid, start, end)
        chart = graphs.calorie_history_chart(daily, user['daily_calorie_target'])
        if chart:
            await query.message.reply_photo(photo=chart, caption="📅 *Calorie History (14 days)*", parse_mode='Markdown')
        else:
            await query.message.reply_text("Not enough data yet.")
        return

    logs = db.get_food_logs_date(uid)
    rda = calc.get_rda(user['age'], user['gender'], user['start_weight_kg'])
    chart = graphs.micronutrient_chart(logs, rda, chart_type)

    labels = {'vitamins': '💊 Vitamins', 'minerals': '⛏️ Minerals', 'amino_acids': '🥩 Amino Acids'}
    if chart:
        await query.message.reply_photo(
            photo=chart,
            caption=f"*{labels.get(chart_type, 'Nutrients')} — Today*\n\n"
                    f"🟢 ≥80%  adequate\n🟡 40–80%  low\n🔴 <40%  deficient",
            parse_mode='Markdown'
        )
    else:
        await query.message.reply_text("No nutrient data available for today yet.")


async def photos_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📤 Upload Photo", callback_data='photo_upload'),
        InlineKeyboardButton("🖼️ View Photos", callback_data='photo_view'),
    ]])
    await update.message.reply_text("📸 *Progress Photos*", parse_mode='Markdown', reply_markup=kb)


async def photos_view_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = update.effective_user.id
    photos = db.get_progress_photos(uid)
    if not photos:
        await query.message.reply_text("No progress photos saved yet.")
        return
    await query.message.reply_text(f"📸 You have {len(photos)} photo(s). Showing last 5:")
    for p in photos[:5]:
        cap = f"📅 {p['photo_date']}"
        if p.get('caption'):
            cap += f"\n{p['caption']}"
        try:
            await query.message.reply_photo(photo=p['file_id'], caption=cap)
        except Exception:
            await query.message.reply_text(f"Could not load photo from {p['photo_date']}")


async def show_profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db.get_user(uid)
    if not user:
        await update.message.reply_text("No profile found. Use /start to set up.")
        return

    act_label = calc.ACTIVITY_LABELS.get(user['activity_level'], user['activity_level'])
    goal_date = calc.get_goal_date(user['created_at'], user['goal_weeks'])

    text = (
        f"👤 *Your Profile*\n\n"
        f"• Name: {user['name']}\n"
        f"• Age: {user['age']}\n"
        f"• Gender: {user['gender'].title()}\n"
        f"• Height: {user['height_cm']:.1f} cm\n"
        f"• Starting weight: {user['start_weight_kg']:.1f} kg\n"
        f"• Goal weight: {user['goal_weight_kg']:.1f} kg\n"
        f"• Activity: {act_label}\n"
        f"• Goal timeline: {user['goal_weeks']} weeks\n"
        f"• Goal date: {goal_date.strftime('%B %d, %Y')}\n\n"
        f"📊 *Daily Targets:*\n"
        f"• BMR: {user['bmr']:.0f} kcal\n"
        f"• TDEE: {user['tdee']:.0f} kcal\n"
        f"• Calorie target: {user['daily_calorie_target']:.0f} kcal\n"
        f"• Protein: {user['protein_target_g']:.0f}g\n"
        f"• Fat: {user['fat_target_g']:.0f}g\n"
        f"• Carbs: {user['carb_target_g']:.0f}g\n\n"
        f"Member since: {user.get('created_at', 'N/A')[:10]}"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑️ Reset All Data", callback_data='reset_prompt'),
    ]])
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=kb)


async def show_goals(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = db.get_user(uid)
    if not user:
        await update.message.reply_text("No profile found. Use /start to set up.")
        return

    logs = db.get_weight_logs(uid, 90)
    current = logs[0]['weight_kg'] if logs else user['start_weight_kg']
    lost = user['start_weight_kg'] - current
    remaining = current - user['goal_weight_kg']
    goal_date = calc.get_goal_date(user['created_at'], user['goal_weeks'])
    deficit = user['tdee'] - user['daily_calorie_target']
    kg_per_week = deficit * 7 / 7700 if deficit > 0 else 0

    # Estimate completion
    if len(logs) >= 2 and lost > 0:
        days_elapsed = (
            __import__('datetime').date.fromisoformat(logs[0]['log_date']) -
            __import__('datetime').date.fromisoformat(logs[-1]['log_date'])
        ).days or 1
        rate = lost / days_elapsed  # kg/day
        days_left = remaining / rate if rate > 0 else None
        est_str = (
            (__import__('datetime').date.today() + __import__('datetime').timedelta(days=days_left)).strftime('%B %d, %Y')
            if days_left else 'N/A'
        )
    else:
        est_str = 'Log more data for estimate'

    text = (
        f"🎯 *Your Goals*\n\n"
        f"*Weight Goal:*\n"
        f"• Start: {user['start_weight_kg']:.1f} kg\n"
        f"• Current: {current:.1f} kg\n"
        f"• Goal: {user['goal_weight_kg']:.1f} kg\n"
        f"• Lost so far: {max(lost,0):.1f} kg\n"
        f"• Remaining: {max(remaining,0):.1f} kg\n\n"
        f"📅 *Timeline:*\n"
        f"• Goal date: {goal_date.strftime('%B %d, %Y')}\n"
        f"• Estimated completion: {est_str}\n\n"
        f"🔥 *Calorie Budget:*\n"
        f"• Daily target: {user['daily_calorie_target']:.0f} kcal\n"
        f"• Daily deficit: {max(deficit,0):.0f} kcal\n"
        f"• Projected loss: ~{kg_per_week:.2f} kg/week"
    )
    await update.message.reply_text(text, parse_mode='Markdown')


# ── Reset flow ───────────────────────────────────────────────────────────────
async def reset_prompt_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("⚠️ YES — Delete Everything", callback_data='reset_confirm'),
        InlineKeyboardButton("❌ Cancel", callback_data='reset_cancel'),
    ]])
    await query.message.reply_text(
        "⚠️ *COMPLETE RESET*\n\n"
        "This will permanently delete:\n"
        "• Your profile\n"
        "• All weight logs\n"
        "• All food logs\n"
        "• All progress photos\n\n"
        "*This cannot be undone!*\n\nAre you sure?",
        parse_mode='Markdown',
        reply_markup=kb
    )


async def reset_confirm_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'reset_confirm':
        db.delete_all_user_data(update.effective_user.id)
        await query.edit_message_text("✅ All data deleted. Send /start to create a new profile.")
    else:
        await query.edit_message_text("Reset cancelled. Your data is safe. ✅")


# ── General callback router ──────────────────────────────────────────────────
async def general_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == 'view_today':
        await query.answer()
        uid = update.effective_user.id
        user = db.get_user(uid)
        logs = db.get_food_logs_date(uid)
        if not logs:
            await query.message.reply_text("No food logged today yet.")
            return
        cal = sum(l['calories'] or 0 for l in logs)
        pro = sum(l['protein_g'] or 0 for l in logs)
        await query.message.reply_text(
            f"📋 *Today's Quick Stats*\n\n"
            f"🔥 Calories: {cal:.0f} / {user['daily_calorie_target']:.0f} kcal\n"
            f"💪 Protein: {pro:.1f} / {user['protein_target_g']:.0f}g",
            parse_mode='Markdown',
            reply_markup=MAIN_KB
        )

    elif data == 'photo_view':
        await photos_view_cb(update, ctx)


# ── Keyboard router ──────────────────────────────────────────────────────────
async def menu_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "Today" in text:
        await today_summary(update, ctx)
    elif "Progress Graph" in text:
        await progress_graph(update, ctx)
    elif "Nutrients" in text:
        await nutrients_menu(update, ctx)
    elif "Progress Photos" in text:
        await photos_menu(update, ctx)
    elif "My Profile" in text:
        await show_profile(update, ctx)
    elif "My Goals" in text:
        await show_goals(update, ctx)


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text("Action cancelled.", reply_markup=MAIN_KB)
    return ConversationHandler.END


# ── /help ────────────────────────────────────────────────────────────────────
async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Weight Loss Tracker — Commands*\n\n"
        "📋 *Main menu buttons:*\n"
        "⚖️ *Log Weight* — record today's weight\n"
        "🍽️ *Log Food* — log food with AI nutrition analysis\n"
        "📊 *Today's Summary* — see today's calories & macros\n"
        "📈 *Progress Graph* — weight loss chart\n"
        "🔬 *Nutrients* — vitamins, minerals, amino acids\n"
        "📸 *Progress Photos* — upload & view progress photos\n"
        "👤 *My Profile* — view your profile & settings\n"
        "🎯 *My Goals* — weight & calorie goals\n\n"
        "📱 *Commands:*\n"
        "/start — set up profile\n"
        "/help — this help message\n"
        "/cancel — cancel current action",
        parse_mode='Markdown',
        reply_markup=MAIN_KB
    )


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    db.init_db()

    if not os.environ.get('ANTHROPIC_API_KEY'):
        print("⚠️  WARNING: ANTHROPIC_API_KEY not set.")
        print("   Food nutrition analysis will not work.")
        print("   Set it with: export ANTHROPIC_API_KEY='your-key-here'")
        print()

    if not BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set. Add it to .env (see .env.example).")

    app = Application.builder().token(BOT_TOKEN).build()

    # Onboarding
    onb_conv = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ONB_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, onb_name)],
            ONB_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, onb_age)],
            ONB_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, onb_gender)],
            ONB_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, onb_height)],
            ONB_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, onb_weight)],
            ONB_GOAL_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, onb_goal_weight)],
            ONB_ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, onb_activity)],
            ONB_GOAL_WEEKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, onb_goal_weeks)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True,
    )

    # Weight logging
    weight_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^⚖️ Log Weight$'), log_weight_start),
            CommandHandler('log_weight', log_weight_start),
        ],
        states={
            W_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, log_weight_value)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Food logging (also entry from "log more food" callback)
    food_conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^🍽️ Log Food$'), log_food_start),
            CommandHandler('log_food', log_food_start),
            CallbackQueryHandler(log_food_start, pattern='^log_more_food$'),
        ],
        states={
            F_MEAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, food_meal)],
            F_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, food_desc)],
            F_CONFIRM: [CallbackQueryHandler(food_confirm, pattern='^food_')],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False,
    )

    # Photo upload conversation
    photo_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(photo_upload_start, pattern='^photo_upload$')],
        states={
            PH_RECEIVE: [MessageHandler(filters.PHOTO, photo_receive)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_message=False,
    )

    app.add_handler(onb_conv)
    app.add_handler(weight_conv)
    app.add_handler(food_conv)
    app.add_handler(photo_conv)

    # Callback handlers (non-conversation)
    app.add_handler(CallbackQueryHandler(nutrients_cb, pattern='^nutr_'))
    app.add_handler(CallbackQueryHandler(reset_prompt_cb, pattern='^reset_prompt$'))
    app.add_handler(CallbackQueryHandler(reset_confirm_cb, pattern='^reset_(confirm|cancel)$'))
    app.add_handler(CallbackQueryHandler(general_cb, pattern='^(view_today|photo_view)$'))

    # Commands
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('today', today_summary))
    app.add_handler(CommandHandler('progress', progress_graph))
    app.add_handler(CommandHandler('nutrients', nutrients_menu))
    app.add_handler(CommandHandler('profile', show_profile))
    app.add_handler(CommandHandler('goals', show_goals))

    # Keyboard menu router (catch-all for main menu text)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND &
        filters.Regex("Today|Progress Graph|Nutrients|Progress Photos|My Profile|My Goals"),
        menu_router
    ))

    print("🤖 Weight Loss Tracker Bot is running!")
    print("   Press Ctrl+C to stop.\n")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
