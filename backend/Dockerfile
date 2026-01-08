# syntax=docker/dockerfile:1.5

# ============================================================================
# Build Stage - Frontend
# ============================================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package.json ./

# Install dependencies (NEVER use npm ci - always use npm install)
RUN --mount=type=cache,target=/root/.npm \
    npm install && \
    npm cache clean --force

# Copy frontend source
COPY frontend/ ./

# Build frontend
RUN npm run build

# ============================================================================
# Build Stage - Backend
# ============================================================================
FROM python:3.11-slim AS backend-builder

WORKDIR /app/backend

# Install build dependencies
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements.txt ./

# Install Python packages
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user --no-cache-dir --no-warn-script-location \
    -r requirements.txt

# ============================================================================
# Runtime Stage
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appgroup && \
    useradd -r -g appgroup -u 1000 appuser && \
    mkdir -p /app/backend /app/frontend/dist && \
    chown -R appuser:appgroup /app

# Copy Python packages from builder
COPY --from=backend-builder --chown=appuser:appgroup /root/.local /home/appuser/.local

# Copy backend application
COPY --chown=appuser:appgroup backend/ /app/backend/

# Copy frontend build artifacts
COPY --from=frontend-builder --chown=appuser:appgroup /app/frontend/dist /app/frontend/dist

# Environment setup
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/backend \
    PORT=8000

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use tini for proper signal handling
ENTRYPOINT ["tini", "--"]

# Start command
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]