# syntax=docker/dockerfile:1

# --- Stage 1: build the React frontend ---
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python runtime serving the app + API on one port ---
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

# Install deps first for better layer caching
COPY requirements.txt pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install -r requirements.txt && pip install -e .

# Committed artifacts so the container runs out of the box (data self-seeds).
COPY models/ ./models/
COPY reports/ ./reports/

# Built SPA from stage 1 — FastAPI serves it from the same origin.
COPY --from=frontend /app/frontend/dist ./frontend/dist

EXPOSE 8000
# Add LLM/Razorpay keys at runtime with `-e`, e.g. -e LLM_PROVIDER=groq -e GROQ_API_KEY=...
CMD ["uvicorn", "recovery.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
