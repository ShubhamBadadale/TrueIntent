FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY mcdc ./mcdc
COPY api ./api
COPY examples ./examples
COPY grammar ./grammar
RUN pip install --no-cache-dir -e . uvicorn

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
