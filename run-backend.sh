#!/usr/bin/env bash
cd backend
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

echo "Starting TrueIntent FastAPI backend on http://localhost:8000..."
uvicorn app.main:app --reload --port 8000
