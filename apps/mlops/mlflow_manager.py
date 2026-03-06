"""
SAHARYN AI — MLflow Experiment Tracking & Model Registry
=========================================================
Production-grade MLOps: tracks every training run, logs metrics,
registers models, and manages promotion from staging to production.

Usage:
    from apps.mlops.mlflow_manager import SAHARYNMLflow
    
    tracker = SAHARYNMLflow()
    with tracker.start_run("dust_severity_model") as run:
        tracker.log_params({"learning_rate": 0.01, "n_estimators": 300})
        tracker.log_metrics({"rmse": 0.042, "r2": 0.94})
        tracker.register_model(model, "DustSeverityModel")
"""

import os
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional
from contextlib import contextmanager

import mlflow
import mlflow.sklearn
import mlflow.xgboost
from mlflow.tracking import MlflowClient
from mlflow.entities import ViewType

logger = logging.getLogger("SAHARYN_MLFLOW")

# ─────────────────────────────────────────────────────────────
# Configuration — all from environment variables
# ─────────────────────────────────────────────────────────────
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_EXPERIMENT_PREFIX = "SAHARYN"

# Model names in the registry — consistent naming enforced here
MODEL_REGISTRY = {
    "dust_severity":       "SAHARYN-DustSeverityModel",
    "asset_performance":   "SAHARYN-AssetPerformanceModel",
    "causal_graph":        "SAHARYN-CausalGraphModel",
    "failure_predictor":   "SAHARYN-FailurePredictorModel",
}

# Production promotion threshold — model must beat this on validation set
PROMOTION_THRESHOLDS = {
    "SAHARYN-DustSeverityModel":     {"rmse": 0.08,  "r2": 0.88},
    "SAHARYN-AssetPerformanceModel": {"mae":  5.0,   "r2": 0.85},
    "SAHARYN-FailurePredictorModel": {"auc":  0.90,  "f1": 0.82},
}


class SAHARYNMLflow:
    """
    Central MLOps manager for all SAHARYN model lifecycle operations.
    
    Responsibilities:
      - Experiment tracking (params, metrics, artifacts)
      - Model registration and versioning
      - Staging → Production promotion with quality gates
      - Model comparison and rollback support
    """

    def __init__(self):
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        self.client = MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)
        logger.info(f"MLflow connected: {MLFLOW_TRACKING_URI}")

    def get_or_create_experiment(self, model_key: str) -> str:
        """Get experiment ID by name, create if it doesn't exist."""
        experiment_name = f"{MLFLOW_EXPERIMENT_PREFIX}/{model_key}"
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if experiment is None:
            experiment_id = mlflow.create_experiment(
                name=experiment_name,
                tags={
                    "project": "SAHARYN",
                    "model_key": model_key,
                    "environment": os.getenv("SAHARYN_ENV", "PRODUCTION"),
                    "created_by": "SAHARYNMLflow",
                }
            )
            logger.info(f"Created experiment: {experiment_name} (ID: {experiment_id})")
            return experiment_id
        return experiment.experiment_id

    @contextmanager
    def start_run(
        self,
        model_key: str,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ):
        """
        Context manager for a training run.
        
        Example:
            with tracker.start_run("dust_severity") as run:
                tracker.log_params({...})
                tracker.log_metrics({...})
        """
        experiment_id = self.get_or_create_experiment(model_key)
        run_name = run_name or f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

        base_tags = {
            "model_key": model_key,
            "git_commit": os.getenv("GITHUB_SHA", "local"),
            "run_environment": os.getenv("SAHARYN_ENV", "PRODUCTION"),
        }
        if tags:
            base_tags.update(tags)

        with mlflow.start_run(
            experiment_id=experiment_id,
            run_name=run_name,
            tags=base_tags,
        ) as run:
            logger.info(f"MLflow run started: {run.info.run_id} | {run_name}")
            self._active_run = run
            try:
                yield run
            except Exception as e:
                mlflow.set_tag("run_status", "FAILED")
                mlflow.set_tag("error", str(e))
                logger.error(f"MLflow run failed: {e}")
                raise
            else:
                mlflow.set_tag("run_status", "SUCCESS")
                logger.info(f"MLflow run completed: {run.info.run_id}")

    def log_params(self, params: Dict[str, Any]) -> None:
        """Log hyperparameters for the active run."""
        mlflow.log_params(params)
        logger.info(f"Logged {len(params)} params")

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None) -> None:
        """Log evaluation metrics. Called after each epoch or after final evaluation."""
        mlflow.log_metrics(metrics, step=step)
        logger.info(f"Logged metrics: {metrics}")

    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None) -> None:
        """Log a file artifact (e.g., feature importance plot, confusion matrix)."""
        mlflow.log_artifact(local_path, artifact_path)

    def register_model(
        self,
        model: Any,
        model_key: str,
        flavor: str = "sklearn",
        input_example: Optional[Any] = None,
    ) -> "mlflow.entities.model_registry.ModelVersion":
        """
        Log and register a trained model in the MLflow Model Registry.
        Returns the ModelVersion object.
        """
        registered_name = MODEL_REGISTRY.get(model_key, f"SAHARYN-{model_key}")

        log_fn = {
            "sklearn":  mlflow.sklearn.log_model,
            "xgboost":  mlflow.xgboost.log_model,
        }.get(flavor, mlflow.sklearn.log_model)

        model_info = log_fn(
            model,
            artifact_path="model",
            registered_model_name=registered_name,
            input_example=input_example,
        )

        logger.info(f"Model registered: {registered_name} | URI: {model_info.model_uri}")
        return model_info

    def promote_to_production(
        self,
        model_key: str,
        version: int,
        validation_metrics: Dict[str, float],
    ) -> bool:
        """
        Promote a model version to Production after passing quality gates.
        Returns True if promoted, False if quality gate failed.
        
        Quality gate: model must beat PROMOTION_THRESHOLDS.
        On success: old Production model is moved to Archived.
        """
        registered_name = MODEL_REGISTRY.get(model_key, f"SAHARYN-{model_key}")
        thresholds = PROMOTION_THRESHOLDS.get(registered_name, {})

        # Quality gate check
        for metric, threshold in thresholds.items():
            actual = validation_metrics.get(metric)
            if actual is None:
                logger.warning(f"Quality gate: metric '{metric}' not found in validation results")
                continue
            # For error metrics (rmse, mae): lower is better
            # For score metrics (r2, auc, f1): higher is better
            is_error_metric = metric in ("rmse", "mae", "mse", "loss")
            passed = (actual <= threshold) if is_error_metric else (actual >= threshold)
            if not passed:
                logger.error(
                    f"QUALITY GATE FAILED: {metric}={actual:.4f} "
                    f"(threshold: {'<=' if is_error_metric else '>='} {threshold})"
                )
                return False

        # Archive any existing Production version
        try:
            prod_versions = self.client.get_latest_versions(
                registered_name, stages=["Production"]
            )
            for old_version in prod_versions:
                self.client.transition_model_version_stage(
                    name=registered_name,
                    version=old_version.version,
                    stage="Archived",
                    archive_existing_versions=False,
                )
                logger.info(f"Archived old production model: v{old_version.version}")
        except Exception:
            pass  # No existing production version — that's fine

        # Promote new version
        self.client.transition_model_version_stage(
            name=registered_name,
            version=str(version),
            stage="Production",
        )
        logger.info(f"PROMOTED: {registered_name} v{version} → Production")
        return True

    def load_production_model(self, model_key: str) -> Any:
        """
        Load the current Production model for inference.
        Raises ValueError if no production model is registered.
        """
        registered_name = MODEL_REGISTRY.get(model_key, f"SAHARYN-{model_key}")
        model_uri = f"models:/{registered_name}/Production"
        try:
            model = mlflow.pyfunc.load_model(model_uri)
            logger.info(f"Loaded production model: {registered_name}")
            return model
        except Exception as e:
            raise ValueError(
                f"No production model found for '{model_key}'. "
                f"Train and promote a model first. Error: {e}"
            )

    def get_best_run(
        self,
        model_key: str,
        metric: str = "rmse",
        ascending: bool = True,
    ) -> Optional[Dict]:
        """
        Return the best run for a given model by metric.
        Useful for comparing experiments before promoting.
        """
        experiment_name = f"{MLFLOW_EXPERIMENT_PREFIX}/{model_key}"
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if not experiment:
            return None

        order = "ASC" if ascending else "DESC"
        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string="attributes.status = 'FINISHED'",
            order_by=[f"metrics.{metric} {order}"],
            max_results=1,
            run_view_type=ViewType.ACTIVE_ONLY,
        )

        if runs.empty:
            return None

        best = runs.iloc[0]
        return {
            "run_id": best["run_id"],
            "metric_value": best.get(f"metrics.{metric}"),
            "start_time": best.get("start_time"),
            "params": {
                k.replace("params.", ""): v
                for k, v in best.items()
                if k.startswith("params.")
            },
        }

    def list_model_versions(self, model_key: str) -> list:
        """List all registered versions of a model with their stages."""
        registered_name = MODEL_REGISTRY.get(model_key, f"SAHARYN-{model_key}")
        try:
            versions = self.client.search_model_versions(f"name='{registered_name}'")
            return [
                {
                    "version": v.version,
                    "stage": v.current_stage,
                    "run_id": v.run_id,
                    "creation_timestamp": v.creation_timestamp,
                    "description": v.description,
                }
                for v in versions
            ]
        except Exception:
            return []
