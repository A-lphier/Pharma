# Dockerfile - Backend FatturaMVP
# Python 3.12 + FastAPI + Uvicorn + Celery

FROM python:3.12-slim

# Impedisce a Python di creare file .pyc e buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONFAULTHANDLER=1

# Variabili di ambiente per performance
ENV UVICORN_WORKERS=4
ENV UVICORN_LIMIT_CONCURRENCY=100
ENV UVICORN_LIMIT_MAX_REQUESTS=1000

WORKDIR /app

# Installazione dipendenze di sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq-dev \
    gcc \
    g++ \
    # Dipendenze per OCR/parsing PDF (se necessario)
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-ita \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

# Copia requirements prima dell'installazione (per caching)
COPY requirements.txt .

# Installa dipendenze Python in virtualenv
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copia codice applicazione
COPY --chown=appuser:appuser . .

# Crea directory per dati e celerybeat
RUN mkdir -p /app/data/invoices /app/data/uploads /app/celerybeat-schedule && \
    chown -R appuser:appuser /app/data

# Switch a utente non-root
USER appuser

# Esporta PYTHONPATH
ENV PYTHONPATH=/app

# Porta exposed
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default: uvicorn per FastAPI
# Override con docker-compose per celery worker o beat
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers"]
