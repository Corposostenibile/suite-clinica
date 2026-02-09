# ==========================================
# STAGE 1: Frontend Build (Node.js)
# ==========================================
FROM node:20-alpine AS frontend-builder
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
COPY backend/wsgi.py ./

# Build Documentation (MkDocs) - Production Ready
# Generates static HTML files in corposostenibile/blueprints/documentation/static
RUN mkdocs build -f corposostenibile/blueprints/documentation/mkdocs.yml


# Copy built frontend assets from Stage 1
# We allow __init__.py to serve them via send_from_directory
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose port (GCP expects 8080 by default)
EXPOSE 8080

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--timeout", "120", "wsgi:app"]
