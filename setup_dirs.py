import os

dirs = [
    "apps/api_gateway",
    "apps/ingestion/satellite",
    "apps/ingestion/weather",
    "apps/ingestion/scada",
    "apps/ingestion/cmms",
    "apps/processing/temporal_alignment",
    "apps/processing/feature_store",
    "apps/ai_core/environmental_impact",
    "apps/ai_core/asset_performance",
    "apps/ai_core/causal_graph",
    "apps/engines/optimization",
    "apps/engines/financial_simulation",
    "apps/mlops/drift_detection",
    "apps/mlops/retraining",
    "apps/dashboard",
    "core/security",
    "core/common",
    "core/compliance",
    "deployment/k8s",
    "deployment/docker",
    "deployment/edge",
    "deployment/ci_cd",
    "docs/architecture",
    "docs/api",
    "docs/compliance",
    "scripts",
    "tests"
]

for d in dirs:
    os.makedirs(d, exist_ok=True)
    print(f"Created {d}")
