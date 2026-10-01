# TrueIntent — module and tooling paths.
#
# The canonical Python environment for this repository is `.venv/` at the repo
# root, created by ./setup.ps1 (Windows) or ./setup.sh (POSIX). There is no
# `backend/venv`.
#
# The default targets below assume Windows PowerShell paths. Use the `-linux`
# variants on macOS/Linux, or just run ./setup.sh and ./run-backend.sh.
PYTHON ?= .venv/Scripts/python.exe
UVICORN ?= .venv/Scripts/uvicorn.exe

.PHONY: setup setup-linux backend backend-linux frontend test test-linux \
        test-cov frontend-test frontend-lint train-modules clean

# On Windows 'py -3' is the launcher; on POSIX 'python3'. Override with
# `make setup PY=...` if your interpreter lives elsewhere.
PY ?= $(shell command -v py >/dev/null 2>&1 && echo "py -3" || echo python3)

setup:
	$(PY) -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r backend/requirements.txt
	$(PYTHON) -m pip install -r backend/requirements-dev.txt
	cd frontend && npm install

setup-linux:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip
	.venv/bin/python -m pip install -r backend/requirements.txt
	.venv/bin/python -m pip install -r backend/requirements-dev.txt
	cd frontend && npm install

backend:
	$(PYTHON) -m backend --port 8000

backend-linux:
	.venv/bin/python -m backend --port 8000

frontend:
	cd frontend && npm run dev

test:
	$(PYTHON) -m pytest tests

test-linux:
	.venv/bin/python -m pytest tests

test-cov:
	$(PYTHON) -m pytest --cov=backend.app --cov=ml --cov-report=term-missing tests

frontend-test:
	cd frontend && npm test

frontend-lint:
	cd frontend && npm run lint

# Retrain the models a clean checkout can rebuild without licensed data.
# Module A is excluded: it requires authorized IEEE-CIS source data.
train-modules:
	$(PYTHON) ml/train_module_b.py
	$(PYTHON) ml/train_module_c.py
	$(PYTHON) ml/train_module_d.py

clean:
	rm -rf .pytest_cache htmlcov .coverage frontend/dist
	find . -name __pycache__ -type d -prune -exec rm -rf {} +