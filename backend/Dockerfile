# TrueIntent backend — FastAPI + Modules A–D.
# Build context is the REPO ROOT:  docker build -f backend/Dockerfile .
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Tesseract OCR engine binary so screenshot OCR works out of the box
# (pytesseract alone is only a wrapper).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r backend/requirements.txt

COPY backend/ ./backend/
COPY ml/ ./ml/
COPY data/ ./data/

# Train Module A at build time. Deterministic (seed 42): regenerates the
# synthetic dataset if absent and bakes an identical artifact every build,
# so a fresh clone with no data/models still produces a working API.
RUN python ml/train_module_a.py

WORKDIR /app/backend
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
