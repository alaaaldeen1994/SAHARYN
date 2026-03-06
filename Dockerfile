# SAHARYN AI v2.1 - INSTITUTIONAL PRODUCTION CONTAINER
# Target: Railway.app / Enterprise Cloud / High-Availability Clusters

FROM python:3.11-slim

WORKDIR /app

# System Dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python Requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy All Logic & Assets
COPY services/ ./services/
COPY apps/ ./apps/
COPY core/ ./core/
COPY infrastructure/ ./infrastructure/
# Copy metadata/configs if needed
COPY README.md .

# Security: Run as non-privileged user
RUN addgroup --system saharyn && adduser --system --group saharyn
RUN chown -R saharyn:saharyn /app
USER saharyn

# Deployment Environment
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/app
ENV PORT=8005

EXPOSE 8005

# Execute High-Fidelity API Gateway
CMD ["python", "apps/api_gateway/main.py"]
