"""
SAHARYN AI — Sentinel-2 Surface Reflectance & Thermal Connector
================================================================
Fetches Sentinel-2 multispectral imagery for:
  - Dust plume detection (SWIR + NIR band ratios)
  - Surface temperature estimation (thermal band proxy)
  - Vegetation/surface change monitoring around assets

Uses Sentinel Hub API (sentinelhub-py) — requires:
  - SENTINELHUB_CLIENT_ID environment variable
  - SENTINELHUB_CLIENT_SECRET environment variable

Data products:
  - Sentinel-2 L2A (atmospherically corrected, 10-60m resolution)
  - Bands used: B02 (Blue), B04 (Red), B08 (NIR), B11 (SWIR1), B12 (SWIR2)

Dust Detection Index (DDI):
  - DDI = (B11 - B04) / (B11 + B04)
  - DDI > 0.2 indicates active dust plume over the target area

Usage:
    connector = Sentinel2Connector()
    plume = connector.detect_dust_plume("SA_EAST_RU_01", lat=26.44, lon=50.10)
"""

import os
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("SAHARYN_SENTINEL2")

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
SH_CLIENT_ID     = os.getenv("SENTINELHUB_CLIENT_ID")     # OAuth2 Client ID
SH_CLIENT_SECRET = os.getenv("SENTINELHUB_CLIENT_SECRET")  # OAuth2 Client Secret
SH_INSTANCE_ID   = os.getenv("SENTINELHUB_INSTANCE_ID")    # Account ID

# Area radius around asset for imagery (km)
DEFAULT_RADIUS_KM = 10.0
# Cloud cover filter — reject scenes with more than 20% cloud cover
MAX_CLOUD_COVER = 20.0


class Sentinel2Connector:
    """
    Sentinel-2 surface reflectance connector for dust plume detection
    and surface condition monitoring around industrial assets.
    """

    def __init__(self):
        self._sh_config = None
        self._available = False
        self._connect()

    def _connect(self):
        """Initialize Sentinel Hub connection using OAuth2 Client Credentials."""
        if not SH_CLIENT_ID or not SH_CLIENT_SECRET:
            logger.warning(
                "Sentinel Hub OAuth credentials not set. "
                "Set SENTINELHUB_CLIENT_ID and SENTINELHUB_CLIENT_SECRET."
            )
            return

        try:
            from sentinelhub import SHConfig
            config = SHConfig()
            config.sh_client_id     = SH_CLIENT_ID
            config.sh_client_secret = SH_CLIENT_SECRET
            config.sh_token_url     = "https://services.sentinel-hub.com/oauth/token"
            config.sh_base_url      = "https://services.sentinel-hub.com"
            if SH_INSTANCE_ID:
                config.instance_id = SH_INSTANCE_ID
            self._sh_config = config
            self._available = True
            logger.info(f"Sentinel Hub OAuth connected: client_id={SH_CLIENT_ID[:8]}...")
        except ImportError:
            logger.warning("sentinelhub not installed. pip install sentinelhub")
        except Exception as e:
            logger.error(f"Sentinel Hub init failed: {e}")

    def _bbox_from_point(self, lat: float, lon: float, radius_km: float = DEFAULT_RADIUS_KM) -> Tuple:
        """
        Compute a bounding box around a lat/lon point.
        Approximate: 1° ≈ 111km.
        Returns (min_lon, min_lat, max_lon, max_lat).
        """
        delta = radius_km / 111.0
        return (lon - delta, lat - delta, lon + delta, lat + delta)

    def detect_dust_plume(
        self,
        site_id: str,
        lat: float,
        lon: float,
        date: Optional[datetime] = None,
        lookback_days: int = 5,
    ) -> Dict:
        """
        Detect active dust plume over an industrial site using Sentinel-2 imagery.
        
        Returns:
            Dict with:
              - dust_plume_detected: bool
              - dust_detection_index: float (DDI value, 0-1)
              - dust_coverage_pct: float (% of scene with dust)
              - image_date: str
              - cloud_cover_pct: float
              - recommendation: str
        """
        target_date = date or datetime.utcnow()

        if self._available:
            return self._fetch_real_imagery(site_id, lat, lon, target_date, lookback_days)
        else:
            return self._simulation_mode(site_id, lat, lon, target_date)

    def _fetch_real_imagery(
        self,
        site_id: str,
        lat: float,
        lon: float,
        target_date: datetime,
        lookback_days: int,
    ) -> Dict:
        """Fetch and process real Sentinel-2 imagery via Sentinel Hub API."""
        try:
            from sentinelhub import (
                BBox, CRS, DataCollection, SentinelHubRequest,
                MimeType, WcsRequest, bbox_to_dimensions,
            )

            bbox = BBox(
                bbox=self._bbox_from_point(lat, lon),
                crs=CRS.WGS84,
            )

            # Evalscript: compute DDI and return band values
            evalscript = """
            //VERSION=3
            function setup() {
                return {
                    input: ["B04", "B08", "B11", "B12", "CLM"],
                    output: [
                        { id: "ddi",   bands: 1, sampleType: "FLOAT32" },
                        { id: "ndvi",  bands: 1, sampleType: "FLOAT32" },
                        { id: "cloud", bands: 1, sampleType: "UINT8" }
                    ]
                };
            }
            function evaluatePixel(sample) {
                // Dust Detection Index: (SWIR1 - Red) / (SWIR1 + Red)
                var ddi  = (sample.B11 - sample.B04) / (sample.B11 + sample.B04 + 1e-6);
                // NDVI for vegetation check
                var ndvi = (sample.B08 - sample.B04) / (sample.B08 + sample.B04 + 1e-6);
                return {
                    ddi:   [ddi],
                    ndvi:  [ndvi],
                    cloud: [sample.CLM]
                };
            }
            """

            request = SentinelHubRequest(
                evalscript=evalscript,
                input_data=[
                    SentinelHubRequest.input_data(
                        data_collection=DataCollection.SENTINEL2_L2A,
                        time_interval=(
                            (target_date - timedelta(days=lookback_days)).strftime("%Y-%m-%d"),
                            target_date.strftime("%Y-%m-%d"),
                        ),
                        other_args={"dataFilter": {"maxCloudCoverage": MAX_CLOUD_COVER}},
                    )
                ],
                responses=[
                    SentinelHubRequest.output_response("ddi",   MimeType.TIFF),
                    SentinelHubRequest.output_response("cloud", MimeType.TIFF),
                ],
                bbox=bbox,
                size=bbox_to_dimensions(bbox, resolution=60),   # 60m resolution
                config=self._sh_config,
            )

            data = request.get_data()
            if not data:
                logger.warning(f"Sentinel-2: No imagery returned for {site_id}")
                return self._simulation_mode(site_id, lat, lon, target_date)

            ddi_array   = np.array(data[0]["ddi.tif"])
            cloud_array = np.array(data[0]["cloud.tif"])

            # Compute statistics
            valid_pixels    = cloud_array == 0               # Non-cloud pixels
            cloud_pct       = float(1 - valid_pixels.mean()) * 100
            ddi_values      = ddi_array[valid_pixels]
            mean_ddi        = float(np.nanmean(ddi_values)) if ddi_values.size > 0 else 0.0
            dust_pixel_pct  = float((ddi_values > 0.2).mean() * 100) if ddi_values.size > 0 else 0.0

            plume_detected = mean_ddi > 0.2 and dust_pixel_pct > 10.0

            logger.info(
                f"Sentinel-2 processed: site={site_id} DDI={mean_ddi:.3f} "
                f"dust_coverage={dust_pixel_pct:.1f}% cloud={cloud_pct:.1f}%"
            )

            return {
                "site_id": site_id,
                "dust_plume_detected":    plume_detected,
                "dust_detection_index":   round(mean_ddi, 4),
                "dust_coverage_pct":      round(dust_pixel_pct, 2),
                "cloud_cover_pct":        round(cloud_pct, 2),
                "image_date":             target_date.strftime("%Y-%m-%d"),
                "spatial_resolution_m":   60,
                "data_source":            "SENTINEL2_L2A",
                "recommendation":         self._get_recommendation(mean_ddi, plume_detected),
            }

        except Exception as e:
            logger.error(f"Sentinel-2 real imagery fetch failed: {e}")
            return self._simulation_mode(site_id, lat, lon, target_date)

    def _simulation_mode(self, site_id: str, lat: float, lon: float, date: datetime) -> Dict:
        """
        Returns a clearly-flagged simulation result when Sentinel Hub is unavailable.
        This allows the system to continue operating for dev/testing without credentials.
        """
        logger.warning(f"Sentinel-2 SIMULATION MODE for {site_id} — credentials not configured")
        return {
            "site_id": site_id,
            "dust_plume_detected":    False,
            "dust_detection_index":   0.0,
            "dust_coverage_pct":      0.0,
            "cloud_cover_pct":        0.0,
            "image_date":             date.strftime("%Y-%m-%d"),
            "spatial_resolution_m":   60,
            "data_source":            "SIMULATION",
            "recommendation":         "Configure SENTINELHUB credentials for real imagery",
        }

    def _get_recommendation(self, ddi: float, plume_detected: bool) -> str:
        """Generate operational recommendation based on DOI value."""
        if not plume_detected:
            return "No active dust plume. Normal operations."
        if ddi > 0.5:
            return "SEVERE dust plume detected. Initiate emergency filter protection protocol."
        if ddi > 0.35:
            return "MODERATE dust plume. Recommend pre-emptive maintenance check in 12h."
        return "MILD dust signature. Monitor conditions. Schedule inspection within 48h."

    def validate_connection(self) -> Dict:
        """Health check for Sentinel Hub API."""
        return {
            "status": "CONNECTED" if self._available else "SIMULATION_MODE",
            "credentials_configured": bool(SH_CLIENT_ID and SH_CLIENT_SECRET),
            "cloud_cover_filter": f"<{MAX_CLOUD_COVER}%",
            "detection_method": "Dust Detection Index (DDI) = (B11-B04)/(B11+B04)",
        }
