#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "=========================================="
echo "      TrueIntent Development Setup       "
echo "=========================================="

if [ ! -d ".venv" ]; then
    echo "[1/3] Creating virtual environment at .venv ..."
    python3 -m venv .venv || python -m venv .venv
else
    echo "[1/3] Reusing existing .venv"
fi

PYTHON=".venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    PYTHON=".venv/Scripts/python.exe"
fi

echo "[2/3] Installing Python dependencies from backend/requirements.txt ..."
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r backend/requirements.txt

echo "[3/3] Installing frontend dependencies ..."
(cd frontend && npm install)

echo "=========================================="
echo " Setup complete. Run backend and frontend:"
echo "   ./run-backend.sh"
echo "   ./run-frontend.sh"
echo " Tests: $PYTHON -m pytest"
echo "=========================================="