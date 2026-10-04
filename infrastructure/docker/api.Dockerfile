FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY apps/api /app
COPY dataset /app/dataset
RUN pip install --no-cache-dir .

ENV VERIDEX_STORAGE_ROOT=/data
ENV VERIDEX_REPO_ROOT=/app
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn veridex.api.app:app --host 0.0.0.0 --port 8000"]
