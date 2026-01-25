# HomeSentry Docker Image
# Base image: Python 3.11 slim (Debian-based, minimal size)
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies
# - curl: for health checks
# - procps: for process monitoring tools
# - ca-certificates: for HTTPS requests
# - sqlite3: for database inspection and debugging
RUN apt-get update && apt-get install -y \
    curl \
    procps \
    ca-certificates \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements first (for Docker layer caching)
# This layer only rebuilds if requirements.txt changes
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir: Don't cache pip downloads (saves space)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Expose port 8000 (FastAPI default)
EXPOSE 8000

# Health check configuration
# Docker will periodically hit this endpoint to verify container health
# --interval=30s: Check every 30 seconds
# --timeout=10s: Fail if check takes > 10 seconds
# --start-period=5s: Don't check for first 5 seconds (startup grace period)
# --retries=3: Mark unhealthy after 3 consecutive failures
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run the application
# uvicorn: ASGI server for FastAPI
# app.main:app: Module and FastAPI instance
# --host 0.0.0.0: Listen on all interfaces (required for Docker)
# --port 8000: Default port
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
