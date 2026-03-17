# ==========================================
# STAGE 1a: Clinica Frontend Build (Node.js)
# ==========================================
FROM node:20-alpine AS frontend-builder
ARG VITE_LOOM_PUBLIC_APP_ID=a0db7b3b-987d-4b5f-ae28-67ca5f025c85
ENV VITE_LOOM_PUBLIC_APP_ID=${VITE_LOOM_PUBLIC_APP_ID}
WORKDIR /app
COPY corposostenibile-clinica/package*.json ./frontend/
WORKDIR /app/frontend
# Install dependencies
RUN npm ci
# Copy frontend source
COPY corposostenibile-clinica/ ./
# Build React app
RUN npm run build

# ==========================================
# STAGE 1b: Kanban Tab Build (Node.js)
# ==========================================
FROM node:20-alpine AS kanban-builder
WORKDIR /app
COPY teams-kanban/package*.json ./
RUN npm ci
COPY teams-kanban/ ./
RUN npm run build


# ==========================================
# STAGE 2: Backend Runtime (Python)
# ==========================================
FROM python:3.11-slim
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=corposostenibile \
    PORT=8080

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install "poetry==1.7.1"

# Copy dependency definition
COPY backend/pyproject.toml backend/poetry.lock ./

# Install defaults (no dev dependencies)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

# Copy backend code
COPY backend/corposostenibile ./corposostenibile
COPY backend/scripts ./scripts
COPY backend/migrations ./migrations
COPY backend/wsgi.py ./

# Build Documentation (MkDocs) - Production Ready
# Generates static HTML files in corposostenibile/blueprints/documentation/static
RUN mkdocs build -f corposostenibile/blueprints/documentation/mkdocs.yml

# Ensure upload paths exist even when uploads are provided by PVC (prod) or local volume
RUN mkdir -p /var/corposostenibile/uploads /app/uploads


# Copy built frontend assets from Stage 1a
# We allow __init__.py to serve them via send_from_directory
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Copy built Kanban tab assets from Stage 1b
COPY --from=kanban-builder /app/dist ./teams-kanban/dist

# Expose port (GCP expects 8080 by default)
EXPOSE 8080

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "120", "wsgi:app"]
