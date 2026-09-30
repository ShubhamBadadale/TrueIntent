# TrueIntent backend — FastAPI + Modules A–D.
# Build context is the REPO ROOT:  docker build -f backend/Dockerfile .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Tesseract OCR engine binary so screenshot OCR works out of the box
# (pytesseract alone is only a wrapper).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r backend/requirements.txt

COPY backend/ ./backend/
COPY ml/ ./ml/

# Mount trusted, pre-trained artifacts read-only; builds never train models.
RUN useradd --create-home appuser
USER appuser

WORKDIR /app/backend
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
