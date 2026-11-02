FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/data/questionnaires.sqlite3

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --create-home --uid 10001 app

RUN mkdir -p /data && chown app:app /data
USER app
EXPOSE 8080

CMD ["uvicorn", "whale_auth_tools.app:app", "--host", "0.0.0.0", "--port", "8080"]
