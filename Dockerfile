FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini ./

RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin appuser

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/openapi.json')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
