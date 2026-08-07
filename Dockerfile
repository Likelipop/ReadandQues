FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    python -m spacy download en_core_web_sm

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/staticfiles /app/logs /app/ReadAndQues/media && \
    chown -R appuser:appuser /app

COPY --chown=appuser:appuser . /app/

USER appuser

EXPOSE 8000

CMD ["gunicorn", "--config", "/app/gunicorn.conf.py", "--chdir", "/app/ReadAndQues", "ReadAndQues.wsgi:application"]
