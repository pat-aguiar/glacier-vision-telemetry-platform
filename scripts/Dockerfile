FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app/ ./app/
COPY scripts/ ./scripts/

RUN pip install --no-cache-dir . httpx

ENTRYPOINT ["python", "scripts/mock_event_generator.py"]
