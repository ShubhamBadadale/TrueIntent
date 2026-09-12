#!/usr/bin/env bash
set -e

echo "=========================================="
echo "      TrueIntent Development Setup       "
echo "=========================================="

echo "[1/2] Setting up Backend Python environment..."
cd backend
if [ ! -d "venv" ]; then
    python3 -m venv venv || python -m venv venv
fi

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

pip install --upgrade pip
pip install -r requirements.txt
cd ..

echo "[2/2] Setting up Frontend dependencies..."
cd frontend
npm install
cd ..

echo "=========================================="
echo " Setup complete! Run backend and frontend:"
echo "   ./run-backend.sh"
echo "   ./run-frontend.sh"
echo "=========================================="
