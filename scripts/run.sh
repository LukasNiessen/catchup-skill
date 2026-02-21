#!/usr/bin/env bash
# Wrapper: finds python3 or python, then runs the requested script.
# Usage: bash run.sh <script.py> [args...]
PY=$(python3 -c "" 2>/dev/null && echo python3 || echo python)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$PY" "$SCRIPT_DIR/$@"
