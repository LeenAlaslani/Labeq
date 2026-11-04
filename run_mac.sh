#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example; add your own keys locally (never commit it)."
fi
if [ ! -d .venv ]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install -q -r requirements.txt
PORT="${LABEQ_PORT:-8006}"
if command -v lsof >/dev/null 2>&1; then
  while lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; do PORT=$((PORT+1)); done
fi
printf 'LABEQ web app: http://127.0.0.1:%s\n' "$PORT"
python -m uvicorn app:app --host 127.0.0.1 --reload --port "$PORT"
