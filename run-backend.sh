#!/usr/bin/env bash
# Start the TrueIntent FastAPI backend on http://localhost:8000
# Uses the repo-root .venv created by setup.sh.
set -euo pipefail
cd "$(dirname "$0")"

if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif [ -x ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
else
    echo "No .venv found. Run ./setup.sh first." >&2
    exit 1
fi

echo "Starting TrueIntent FastAPI backend on http://localhost:8000..."
echo "Docs: http://localhost:8000/docs   Health: http://localhost:8000/health   Ready: http://localhost:8000/ready"
exec "$PYTHON" -m backend --port 8000