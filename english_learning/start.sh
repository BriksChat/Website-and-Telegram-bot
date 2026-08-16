#!/bin/sh
set -eu
gunicorn --bind "0.0.0.0:${PORT:-5000}" app.server:app &
api_pid=$!
if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  python -m bot.launch_bot &
  bot_pid=$!
  trap 'kill "$api_pid" "$bot_pid" 2>/dev/null || true' INT TERM
else
  echo 'TELEGRAM_BOT_TOKEN is not set; starting API without Telegram bot' >&2
  trap 'kill "$api_pid" 2>/dev/null || true' INT TERM
fi
wait "$api_pid"
