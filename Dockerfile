# ── Frontend build ──────────────────────────────────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /app

COPY package.json ./
COPY frontend/package.json ./frontend/

RUN cd frontend && npm install

COPY frontend/ ./frontend/

RUN cd frontend && npm run build

# ── Python runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./static

ENV PYTHONPATH=/app/backend
ENV DROIDLENS_STATIC_DIR=/app/static
ENV DROIDLENS_HOST=0.0.0.0
ENV DROIDLENS_MOCK=true
ENV DROIDLENS_LOG_LEVEL=INFO

EXPOSE 8765

WORKDIR /app/backend

CMD ["python3", "-m", "inspectiq.api.main"]
