# Usage guide

## 1. Setup

### Create a Telegram bot
1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot`, choose a display name and a username ending in `bot`.
3. Copy the token BotFather gives you.

### Get an Anthropic API key
Create one at [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys). It's used to analyse the food you log.

### Install and configure
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```
Edit `.env`:
```
TELEGRAM_BOT_TOKEN=123456789:your-token-here
ANTHROPIC_API_KEY=sk-ant-...
```
> `.env` is git-ignored — never commit it.

### Run
```bash
./run.sh
```
The bot runs until you stop it (Ctrl+C). The database is created automatically at `data/tracker.db`, and logs go to the terminal.

## 2. First conversation — `/start`

Send `/start` to your bot. It walks you through your profile one question at a time:

1. **Name**
2. **Age**
3. **Sex** (used in the BMR formula)
4. **Height** — `175`, `175cm`, `5'10"` or `5 10`
5. **Current weight** — `80.5`, `80.5 kg` or `177 lbs`
6. **Goal weight**
7. **Activity level** — pick from the buttons:

   | Level | Multiplier |
   |---|---|
   | 🪑 Sedentary | 1.2 |
   | 🚶 Lightly active (1–3 days/week) | 1.375 |
   | 🏃 Moderately active (3–5 days/week) | 1.55 |
   | 💪 Very active (6–7 days/week) | 1.725 |
   | 🔥 Extra active | 1.9 |

8. **Timeframe** — how many weeks you want to reach your goal in.

The bot then shows your BMR, TDEE, daily calorie target and macro targets, and the main menu appears.

Send `/cancel` at any point to stop the current step.

## 3. Main menu

| Button | What it does |
|---|---|
| ⚖️ **Log Weight** | Record today's weight. |
| 🍽️ **Log Food** | Pick a meal (Breakfast, Lunch, Dinner, Snack, Supplement, Drink), then describe what you ate. |
| 📊 **Today's Summary** | Calories and macros eaten today vs. your targets. |
| 📈 **Progress Graph** | Chart of your weight over time against your goal. |
| 🔬 **Nutrients** | Charts for 💊 vitamins, ⛏️ minerals, 🥩 amino acids (vs. RDA) and 📅 calorie history. |
| 📸 **Progress Photos** | 📤 Upload a photo (add a caption if you like) or 🖼️ view past photos. |
| 👤 **My Profile** | Your stats and settings, plus 🗑️ *Reset All Data*. |
| 🎯 **My Goals** | Goal weight, timeframe, calorie and macro targets. |

## 4. Logging food

Describe the food the way you'd say it out loud — include quantities where you can:

- `2 scrambled eggs and a slice of wholemeal toast with butter`
- `chicken caesar salad, large`
- `250ml semi-skimmed milk`
- `a Mars bar`

The bot sends it to Claude and replies with a breakdown: calories, macros (protein, carbs, fat, fibre, sugar), fat types, and key vitamins and minerals, plus a confidence indicator (🟢 high, 🟡 medium, 🔴 low).

Tap **✅ Save** to log it or **❌ Cancel** to discard it. After saving you can **➕ Log More Food** or **📊 View Today**.

**Tips**
- More specific = more accurate. "100g cooked basmati rice" beats "some rice".
- Log a whole meal in one message, or each item separately for finer detail.
- If the API key is missing, the bot tells you how to set it up.

## 5. Commands

| Command | Description |
|---|---|
| `/start` | Set up your profile (or say welcome back) |
| `/help` | Show the command list |
| `/cancel` | Cancel the current action |
| `/log_weight` | Same as ⚖️ Log Weight |
| `/log_food` | Same as 🍽️ Log Food |
| `/today` | Same as 📊 Today's Summary |
| `/progress` | Same as 📈 Progress Graph |
| `/nutrients` | Same as 🔬 Nutrients |
| `/profile` | Same as 👤 My Profile |
| `/goals` | Same as 🎯 My Goals |

## 6. How the numbers are calculated

- **BMR (Mifflin–St Jeor)**
  - Male: `10 × weight(kg) + 6.25 × height(cm) − 5 × age + 5`
  - Female: `10 × weight(kg) + 6.25 × height(cm) − 5 × age − 161`
- **TDEE** = BMR × activity multiplier (table above)
- **Daily calorie target** = TDEE − daily deficit, where
  `daily deficit = (kg to lose × 7700 kcal) ÷ (weeks × 7)`.
  For safety the deficit is capped at **1000 kcal/day** and the target never drops below **1200 kcal**. If your goal is to gain weight, the target is TDEE + 300.
- **RDA** for vitamins and minerals is based on your age, sex and weight.

## 7. Your data

- All data is stored locally in `data/tracker.db` (SQLite), keyed by your Telegram user ID.
- Food descriptions are sent to the Anthropic API for analysis.
- **👤 My Profile → 🗑️ Reset All Data** permanently deletes your profile, weight and food logs, and saved photo references after a confirmation.

## Troubleshooting

| Problem | Fix |
|---|---|
| `TELEGRAM_BOT_TOKEN is not set` | Add it to `.env`. |
| Food analysis doesn't work | Check `ANTHROPIC_API_KEY` in `.env` and that the key has credit. |
| Bot doesn't reply | Make sure `./run.sh` is still running and the token matches your bot. |
| `ModuleNotFoundError` | Activate the venv and run `pip install -r requirements.txt`. |
