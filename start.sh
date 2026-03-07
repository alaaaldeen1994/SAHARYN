#!/bin/bash
set -e
set -x
echo "SAHARYN AI: Deployment initialization starting..."

# 1. Materialize Database Schema
echo "Step 1/2: Preparing Persistence Layer..."
python init_db.py

# 2. Launch Enterprise API Gateway
echo "Step 2/2: Engaging Mission Control (API Gateway)..."
python apps/api_gateway/main.py
