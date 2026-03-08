"""
SAHARYN AI — Cold Start Model Training
========================================
This script performs the first "real" training of the production models.
It uses high-fidelity synthetic data (physics-informed) to bootstrap
the models into the MLflow Model Registry.

This makes the system "real" from day one.
"""

import logging
import pandas as pd
import numpy as np

from apps.mlops.mlflow_manager import SAHARYNMLflow
from services.ai_core.training_pipeline import TrainingPipelines

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("SAHARYN_COLD_START")

def bootstrap_models():
    """Trains and registers the first set of production models."""
    mlflow_mgr = SAHARYNMLflow()

    # 1. --- Dust Severity Index (DSI) Model ---
    logger.info("Bootstrapping Layer 1: Dust Severity Index model...")
    np.random.seed(42)
    n = 2000
    dsi_data = {
        'aerosol_optical_depth': np.random.uniform(0.1, 2.5, n),
        'wind_speed_10m': np.random.uniform(0, 30, n),
        'temperature_2m_c': np.random.uniform(15, 55, n),
        'relative_humidity_pct': np.random.uniform(2, 45, n),
        'surface_pressure_hpa': np.random.uniform(1000, 1030, n),
    }
    # Physics-informed DSI target (DSI is non-linear and sensitive to dry wind)
    dsi_data['dust_severity_index'] = np.clip(
        (0.55 * dsi_data['aerosol_optical_depth']) +
        (0.40 * (dsi_data['wind_speed_10m'] / 30)**1.8) -
        (0.15 * (dsi_data['relative_humidity_pct'] / 100)),
        0.0, 1.0
    ) + np.random.normal(0, 0.03, n)
    df_dsi = pd.DataFrame(dsi_data)

    with mlflow_mgr.start_run(model_key="dust_severity", run_name="production_bootstrap_v1"):
        model, metrics = TrainingPipelines.train_dust_severity(df_dsi)
        mlflow_mgr.log_metrics(metrics)
        model_info = mlflow_mgr.register_model(model, "dust_severity")
        # Promote to Production immediately for cold start
        mlflow_mgr.promote_to_production("dust_severity", int(model_info.registered_model_version), metrics)
        logger.info(f"DSI Model v{model_info.registered_model_version} promoted to PRODUCTION.")

    # 2. --- Asset Performance Model ---
    logger.info("Bootstrapping Layer 2: Asset Performance model...")
    asset_data = {
        'dust_severity_index': np.random.uniform(0, 1.0, n),
        'vibration_mm_s': np.random.uniform(1.0, 18.0, n),
        'bearing_temp_c': np.random.uniform(45, 105, n),
        'surface_temp_c': np.random.uniform(35, 75, n),
        'load_factor': np.random.uniform(0.4, 1.2, n),
        'differential_pressure_bar': np.random.uniform(0.1, 6.0, n),
    }
    # Efficiency degrades significantly with dust and high vibration
    asset_data['efficiency_pct'] = np.clip(
        0.98 -
        (0.15 * asset_data['dust_severity_index']**1.2) -
        (0.10 * (asset_data['vibration_mm_s'] / 18.0)**2) -
        (0.05 * (asset_data['bearing_temp_c'] - 45) / 60),
        0.5, 1.0
    ) + np.random.normal(0, 0.02, n)
    df_asset = pd.DataFrame(asset_data)

    with mlflow_mgr.start_run(model_key="asset_performance", run_name="production_bootstrap_v1"):
        model, metrics = TrainingPipelines.train_asset_performance(df_asset)
        mlflow_mgr.log_metrics(metrics)
        model_info = mlflow_mgr.register_model(model, "asset_performance")
        mlflow_mgr.promote_to_production("asset_performance", int(model_info.registered_model_version), metrics)
        logger.info(f"Asset Model v{model_info.registered_model_version} promoted to PRODUCTION.")

    logger.info("BOOTSTRAP COMPLETE. System is now running on REAL AI models.")

if __name__ == "__main__":
    bootstrap_models()
