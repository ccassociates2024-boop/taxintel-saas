FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY scripts ./scripts

EXPOSE 8000

# Run Alembic migrations then start the API server.
# The only DDL path is alembic upgrade head — never Base.metadata.create_all().
CMD ["sh", "-c", "set -x && echo PORT=${PORT:-8000} && alembic upgrade head 2>&1 && echo '=== Starting uvicorn ===' && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*' --log-level info 2>&1"]
