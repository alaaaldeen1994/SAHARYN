"""
SAHARYN AI — Feature Store Client
===================================
Simple interface for fetching features from Feast online store
during real-time inference.
"""

import os
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("SAHARYN_FEATURE_STORE")

FEAST_REPO_PATH = os.getenv("FEAST_REPO_PATH", "apps/feature_store")


class SAHARYNFeatureStore:
    """
    Thin wrapper around the Feast FeatureStore for inference-time feature retrieval.
    Falls back gracefully when Feast is unavailable (e.g., edge/offline deployment).
    """

    def __init__(self):
        self._store = None
        self._available = False
        self._connect()

    def _connect(self):
        """Initialize Feast connection. Does not raise — falls back to passthrough."""
        try:
            from feast import FeatureStore
            self._store = FeatureStore(repo_path=FEAST_REPO_PATH)
            self._available = True
            logger.info(f"Feast Feature Store connected: {FEAST_REPO_PATH}")
        except Exception as e:
            logger.warning(
                f"Feast Feature Store unavailable (will use raw inputs): {e}. "
                f"Set FEAST_REPO_PATH and run 'feast apply' to enable."
            )
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def get_online_features(
        self,
        entity_rows: List[Dict[str, Any]],
        features: List[str],
    ) -> Optional[Dict[str, List]]:
        """
        Fetch features from Feast online store.
        Returns None if store is unavailable.

        Args:
            entity_rows: e.g., [{"site_id": "SA_EAST_RU_01"}]
            features: e.g., ["satellite_environmental_features:dust_severity_index"]

        Returns:
            Dict mapping feature name → list of values (one per entity row)
        """
        if not self._available or self._store is None:
            return None

        try:
            response = self._store.get_online_features(
                features=features,
                entity_rows=entity_rows,
            ).to_dict()
            logger.debug(f"Feature store returned {len(response)} features")
            return response
        except Exception as e:
            logger.error(f"Feature retrieval failed: {e}")
            return None

    def get_asset_features(self, asset_id: str) -> Optional[Dict[str, float]]:
        """
        Convenience method: get all operational features for a single asset.
        Returns flat dict mapping feature_name → value, or None on failure.
        """
        entity_rows = [{"asset_id": asset_id}]
        features = [
            "asset_operational_features:vibration_mm_s",
            "asset_operational_features:surface_temp_c",
            "asset_operational_features:efficiency_pct",
            "asset_operational_features:differential_pressure_bar",
            "asset_operational_features:load_factor",
            "asset_operational_features:power_consumption_kw",
            "asset_risk_features:failure_probability",
            "asset_risk_features:remaining_useful_life_hrs",
        ]

        result = self.get_online_features(entity_rows, features)
        if result is None:
            return None

        # Flatten from lists (one per entity) to single values
        return {k: v[0] for k, v in result.items() if v and v[0] is not None}

    def get_site_features(self, site_id: str) -> Optional[Dict[str, float]]:
        """
        Convenience method: get all environmental features for a site.
        """
        entity_rows = [{"site_id": site_id}]
        features = [
            "satellite_environmental_features:aerosol_optical_depth",
            "satellite_environmental_features:dust_severity_index",
            "satellite_environmental_features:wind_speed_10m",
            "satellite_environmental_features:temperature_2m_c",
            "satellite_environmental_features:relative_humidity_pct",
            "satellite_environmental_features:storm_probability_72h",
        ]

        result = self.get_online_features(entity_rows, features)
        if result is None:
            return None

        return {k: v[0] for k, v in result.items() if v and v[0] is not None}
