#!/usr/bin/env bash
# PS1 Valuation Engine — Robust Backend Launcher
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Use virtualenv python if present
if [ -f "$DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$DIR/.venv/bin/python"
    source "$DIR/.venv/bin/activate"
else
    PYTHON_BIN="python3"
fi

# Ensure project root and backend are in PYTHONPATH
export PYTHONPATH="$DIR:$DIR/backend:${PYTHONPATH}"

echo "=========================================================="
echo "⚡ Starting PS1 Valuation Engine Backend on http://localhost:8000"
echo "🐍 Python: $($PYTHON_BIN --version 2>&1)"
echo "📖 Swagger API Docs: http://localhost:8000/docs"
echo "=========================================================="

exec $PYTHON_BIN -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload

