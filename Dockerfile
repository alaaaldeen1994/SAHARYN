# SAHARYN AI v2.0 - PRODUCTION CONTAINERS
# Target: Enterprise Edge Deployment / High-Resource Cloud
# Compliance: ISO 27001 / SOC2 Process Isolation

# BASE STAGE
FROM python:3.11-slim as base

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Mock requirements in-place for build demonstration
RUN echo "fastapi==0.104.1\nuvicorn==0.24.0\npydantic==2.5.2\nrequests==2.31.0\nnumpy==1.26.2\npsycopg2-binary==2.9.9" > requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# --- PRODUCTION STAGE ---
FROM base as final

# Create non-privileged user for security compliance
RUN addgroup --system saharyn && adduser --system --group saharyn
USER saharyn

# Copy Source
COPY --chown=saharyn:saharyn apps/ ./apps/
COPY --chown=saharyn:saharyn services/ ./services/
COPY --chown=saharyn:saharyn infrastructure/ ./infrastructure/

# Environment Defaults
ENV API_GATEWAY_PORT=8002
ENV LOG_LEVEL=INFO

EXPOSE 8002

# Run API Gateway as entrypoint
CMD ["python", "apps/api_gateway/main.py"]
