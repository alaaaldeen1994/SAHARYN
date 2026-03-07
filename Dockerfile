# SAHARYN AI — Edge Node Dockerfile (Purdue Level 3 Architecture)
# -------------------------------------------------------------
FROM python:3.11-slim-bookworm as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim-bookworm
WORKDIR /app

# Install system dependencies (for cfgrib and numerical stability)
RUN apt-get update && apt-get install -y \
    libeccodes-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /root/.local /root/.local
COPY . .

# Environment Defaults
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV SAHARYN_ENV=PRODUCTION
ENV SAHARYN_SATELLITE_MODE=LIVE

# Industrial Compliance: Read-only Root FS support
RUN mkdir -p /app/data/raw/satellite && chmod 777 /app/data/raw/satellite

# Healthcheck for Plant Operators
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/v2/system/health || curl -f http://localhost:8005/v2/system/health || exit 1

# Ensure start script is executable
RUN chmod +x /app/start.sh

# Entrypoint: Initialize DB and Launch API Gateway
CMD ["/bin/bash", "/app/start.sh"]
