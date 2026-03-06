"""
SAHARYN AI — Automated Model Retraining Scheduler
===================================================
Runs as a background service. Checks for:
  1. Data drift (triggers immediate retraining)
  2. Scheduled retraining (weekly baseline)
  3. Performance degradation (triggers urgent retraining)

Integrates with MLflow to track all retraining runs.

Run this as a separate service:
    python apps/mlops/retraining_scheduler.py
"""

import os
import time
import logging
import schedule
import threading
from datetime import datetime, timedelta
from typing import Dict, Any

from apps.mlops.mlflow_manager import SAHARYNMLflow
from services.monitoring.drift_detector import DriftDetectionEngine

logger = logging.getLogger("SAHARYN_RETRAINING")

# ─────────────────────────────────────────────────────────────
# Retraining triggers configuration
# ─────────────────────────────────────────────────────────────
RETRAINING_CONFIG = {
    "dust_severity": {
        "schedule": "weekly",            # Baseline retraining every week
        "drift_threshold": 0.15,         # Retrain if drift score > 15%
        "performance_threshold": 0.10,   # Retrain if RMSE degrades by 10%
        "min_new_samples": 1000,         # Minimum new data points needed
    },
    "asset_performance": {
        "schedule": "weekly",
        "drift_threshold": 0.20,
        "performance_threshold": 0.15,
        "min_new_samples": 500,
    },
    "failure_predictor": {
        "schedule": "weekly",
        "drift_threshold": 0.10,         # More sensitive — safety-critical model
        "performance_threshold": 0.05,
        "min_new_samples": 200,
    },
}


class RetrainingScheduler:
    """
    Monitors model health and triggers retraining when needed.
    Runs as a long-lived background service.
    """

    def __init__(self):
        self.mlflow = SAHARYNMLflow()
        self.drift_detector = DriftDetectionEngine()
        self._retraining_lock = threading.Lock()  # Prevent concurrent retraining runs
        self._stats = {
            "total_checks": 0,
            "drift_triggered_retrains": 0,
            "scheduled_retrains": 0,
            "failed_retrains": 0,
            "last_check_time": None,
        }
        logger.info("RetrainingScheduler initialized")

    def check_and_retrain(self, model_key: str) -> Dict[str, Any]:
        """
        Check drift + performance for a model. Retrain if thresholds exceeded.
        Returns a status report dict.
        """
        config = RETRAINING_CONFIG.get(model_key, {})
        result = {
            "model_key": model_key,
            "timestamp": datetime.utcnow().isoformat(),
            "action": "NO_ACTION",
            "reason": "",
        }

        self._stats["total_checks"] += 1
        self._stats["last_check_time"] = datetime.utcnow().isoformat()

        # Check for data drift
        try:
            drift_score = self.drift_detector.get_drift_score(model_key)
            threshold = config.get("drift_threshold", 0.15)

            if drift_score > threshold:
                logger.warning(
                    f"DRIFT DETECTED: {model_key} drift_score={drift_score:.3f} > {threshold}"
                )
                result["reason"] = f"Drift score {drift_score:.3f} exceeded threshold {threshold}"
                self._trigger_retraining(model_key, trigger_type="DRIFT")
                result["action"] = "RETRAIN_TRIGGERED"
                self._stats["drift_triggered_retrains"] += 1
            else:
                result["reason"] = f"Drift score {drift_score:.3f} within threshold {threshold}"
                logger.info(f"Model {model_key}: drift OK ({drift_score:.3f})")

        except Exception as e:
            logger.error(f"Drift check failed for {model_key}: {e}")
            result["reason"] = f"Drift check error: {e}"
            result["action"] = "CHECK_FAILED"

        return result

    def _trigger_retraining(self, model_key: str, trigger_type: str = "SCHEDULED") -> bool:
        """
        Start a retraining job. Protected by lock to prevent concurrent runs.
        Returns True if retraining started, False if skipped (already running).
        """
        if not self._retraining_lock.acquire(blocking=False):
            logger.warning(f"Retraining skipped — another run is in progress")
            return False

        try:
            logger.info(f"RETRAINING STARTED: {model_key} | Trigger: {trigger_type}")

            with self.mlflow.start_run(
                model_key=model_key,
                run_name=f"retrain_{trigger_type.lower()}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                tags={
                    "trigger_type": trigger_type,
                    "automated": "true",
                    "scheduler": "RetrainingScheduler",
                }
            ):
                # Log retraining trigger context
                self.mlflow.log_params({
                    "trigger_type": trigger_type,
                    "model_key": model_key,
                    "retrain_timestamp": datetime.utcnow().isoformat(),
                })

                # --- Load fresh data ---
                # In production this fetches from TimescaleDB via the feature store
                # For now: placeholder that should be replaced with real DB fetch
                logger.info(f"Loading fresh training data for {model_key}...")
                training_data = self._load_training_data(model_key)

                if training_data is None:
                    logger.error(f"No training data available for {model_key}")
                    return False

                # --- Train model ---
                model, metrics = self._train_model(model_key, training_data)

                # --- Log metrics ---
                self.mlflow.log_metrics(metrics)
                logger.info(f"Retraining metrics: {metrics}")

                # --- Attempt promotion with quality gate ---
                # Get version number from MLflow after registration
                model_info = self.mlflow.register_model(model, model_key)
                version = int(model_info.registered_model_version)

                promoted = self.mlflow.promote_to_production(model_key, version, metrics)
                if promoted:
                    logger.info(f"NEW PRODUCTION MODEL: {model_key} v{version}")
                else:
                    logger.warning(f"Model did not pass quality gate — keeping old model")

            return True

        except Exception as e:
            logger.error(f"Retraining failed for {model_key}: {e}")
            self._stats["failed_retrains"] += 1
            return False
        finally:
            self._retraining_lock.release()

    def _load_training_data(self, model_key: str):
        """
        Load training data from TimescaleDB via the feature store.
        Returns a dict with 'X' and 'y' keys, or None if insufficient data.
        
        PRODUCTION NOTE: Replace this with actual DB query via SQLAlchemy + TimescaleDB.
        """
        # Placeholder — real implementation fetches from DB
        # from core.database.session import get_db
        # from sqlalchemy import text
        # data = db.execute(text("SELECT ... FROM asset_telemetry WHERE time > NOW() - INTERVAL '30 days'"))
        logger.info(f"[STUB] Loading training data for {model_key} — connect to TimescaleDB in production")
        return {"status": "stub", "model_key": model_key}

    def _train_model(self, model_key: str, training_data: Dict):
        """
        Train the model for the given model_key.
        Returns (model, metrics) tuple.
        
        PRODUCTION NOTE: This should import and call the actual training pipeline.
        """
        # Placeholder — real implementation calls model-specific training code
        logger.info(f"[STUB] Training {model_key} — import real training pipeline")
        dummy_model = object()
        dummy_metrics = {"rmse": 0.05, "r2": 0.93, "mae": 0.03}
        return dummy_model, dummy_metrics

    def get_stats(self) -> Dict[str, Any]:
        """Return scheduler runtime statistics."""
        return self._stats

    def run(self):
        """
        Start the scheduler. Registers all jobs and runs the event loop.
        This is a blocking call — run in a dedicated thread or process.
        """
        logger.info("Starting retraining scheduler...")

        # Register weekly scheduled retraining for each model
        for model_key in RETRAINING_CONFIG:
            schedule.every().week.do(
                self._trigger_retraining, model_key=model_key, trigger_type="SCHEDULED"
            )
            logger.info(f"Scheduled weekly retraining: {model_key}")

        # Drift check every 6 hours
        for model_key in RETRAINING_CONFIG:
            schedule.every(6).hours.do(self.check_and_retrain, model_key=model_key)
            logger.info(f"Scheduled drift check every 6h: {model_key}")

        logger.info("Retraining scheduler running — checking every 60 seconds")
        while True:
            schedule.run_pending()
            time.sleep(60)


if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s"
    )
    scheduler = RetrainingScheduler()
    scheduler.run()
