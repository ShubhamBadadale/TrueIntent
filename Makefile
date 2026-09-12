.PHONY: setup backend frontend test clean

setup:
	@echo "Setting up backend Python environment..."
	cd backend && python -m venv venv && .\venv\Scripts\pip install -r requirements.txt
	@echo "Setting up frontend dependencies..."
	cd frontend && npm install

backend:
	@echo "Starting FastAPI backend server..."
	cd backend && .\venv\Scripts\uvicorn app.main:app --reload --port 8000

frontend:
	@echo "Starting React frontend..."
	cd frontend && npm run dev

test:
	@echo "Running tests..."
	cd backend && .\venv\Scripts\pytest ../tests/
