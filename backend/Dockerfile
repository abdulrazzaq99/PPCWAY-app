# The backend, with the Chromium the audit's headless render needs already in the image.
# The base image version must match the playwright version in pyproject.toml.
FROM mcr.microsoft.com/playwright/python:v1.62.0-noble

WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml alembic.ini README.md ./
COPY src ./src
COPY migrations ./migrations
RUN uv pip install --system -e .
ENV PYTHONPATH=/app/src PYTHONUNBUFFERED=1
EXPOSE 8300
# Locally the port is 8300; Cloud Run hands the container its own in PORT.
CMD ["sh", "-c", "alembic upgrade head && uvicorn ppcway.api.app:app --host 0.0.0.0 --port ${PORT:-8300}"]
