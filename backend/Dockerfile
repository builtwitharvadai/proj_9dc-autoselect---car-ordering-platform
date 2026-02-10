# ============================================================================
# Build Stage - Backend
# ============================================================================
FROM python:3.11-slim AS backend-builder

WORKDIR /app/backend

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY requirements.txt ./

# Install Python packages
RUN pip install --user --no-cache-dir --no-warn-script-location \
    -r requirements.txt

# ============================================================================
# Runtime Stage
# ============================================================================
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appgroup && \
    useradd -r -g appgroup -u 1000 appuser && \
    mkdir -p /app/backend && \
    chown -R appuser:appgroup /app

# Copy Python packages from builder
COPY --from=backend-builder --chown=appuser:appgroup /root/.local /home/appuser/.local

# Copy backend application
COPY --chown=appuser:appgroup . /app/backend/

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

# Start command - run migrations then start server
CMD ["sh", "-c", "cd /app/backend && alembic upgrade head && uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4"]