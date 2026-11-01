#!/bin/bash
# Run the Nutrition & Weight Tracker bot

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".env" ]; then
    set -a; source .env; set +a
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo "⚠️  TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and add your token from @BotFather."
    exit 1
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  ANTHROPIC_API_KEY is not set — AI food analysis won't work."
    read -p "Continue anyway? [y/N] " confirm
    [[ "$confirm" =~ ^[Yy] ]] || exit 1
fi

PYTHON="$SCRIPT_DIR/venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python3"

echo "Starting Nutrition & Weight Tracker bot..."
exec "$PYTHON" "$SCRIPT_DIR/bot.py"
