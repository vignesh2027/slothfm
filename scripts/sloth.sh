#!/usr/bin/env bash
# Start what Sloth FM needs on this laptop: Ollama (Gemma) and a local Temporal server, then the night shift.
#   scripts/sloth.sh            # waits for the charger, like a sloth
#   scripts/sloth.sh --now      # start now, even on battery
set -euo pipefail
cd "$(dirname "$0")/.."
HOME_DIR="${SLOTHFM_HOME:-$HOME/.slothfm}"; mkdir -p "$HOME_DIR"
pgrep -x ollama >/dev/null || (ollama serve >"$HOME_DIR/ollama.log" 2>&1 &)
if ! nc -z localhost 7233 2>/dev/null; then
  temporal server start-dev --db-filename "$HOME_DIR/temporal.db" --ui-port 8233 >"$HOME_DIR/temporal.log" 2>&1 &
  until nc -z localhost 7233; do sleep 1; done
fi
exec .venv/bin/python -m slothfm night "$@"
