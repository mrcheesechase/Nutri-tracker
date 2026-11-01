# 🥗 Nutri-tracker

A Telegram bot to help track health goals.

An AI-powered weight-loss and nutrition coach that lives in Telegram.
Describe what you ate in plain English — *"2 eggs and a slice of toast"* — and the bot uses Claude to break it down into calories, macros, vitamins, minerals and amino acids, tracks it against personalised targets, and charts your progress over time.

## Features

- **Guided onboarding** — collects your age, sex, height, weight, activity level and goal, then calculates:
  - BMR (Mifflin–St Jeor) and TDEE
  - a daily calorie target to reach your goal weight on time
  - macro targets and recommended daily intake (RDA) for vitamins and minerals
- **Plain-English food logging** — the Claude API returns a full nutritional profile as structured JSON (calories, macros, fat types, vitamins, minerals, amino acids). Review it, then save or cancel.
- **Daily summary** — calories and macros eaten today vs. your targets.
- **Charts** (matplotlib) — weight progress vs. goal, calorie history, macro summary, and vitamin / mineral / amino-acid intake vs. RDA.
- **Progress photos** — upload photos with captions and browse them later.
- **Profile & goals** — view your stats any time; reset all your data with a confirmation step.
- **Local storage** — everything is kept in a local SQLite database.

## Tech stack

Python · [python-telegram-bot](https://python-telegram-bot.org/) · [Anthropic Claude API](https://docs.anthropic.com/) · SQLite · matplotlib · NumPy · Pillow

## Quick start

```bash
git clone https://github.com/mrcheesechase/Nutri-tracker.git
cd Nutri-tracker

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then fill in your two keys
./run.sh
```

You need:

| Variable | Where to get it |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/settings/keys) |

Then open your bot in Telegram and send `/start`.

📖 **Full guide:** [docs/USAGE.md](docs/USAGE.md)

## Project structure

```
bot.py            Telegram handlers, conversations and menus
nutrition.py      Claude API food analysis + formatting
calculations.py   BMR, TDEE, calorie/macro targets, RDA, progress stats
graphs.py         matplotlib charts sent back as images
database.py       SQLite schema and queries (data/tracker.db)
run.sh            Loads .env and starts the bot
```

## Disclaimer

Nutrition values are AI estimates and calorie targets come from standard formulas. This is a personal project, not medical advice.
