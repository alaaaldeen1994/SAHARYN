"""
SAHARYN AI — AVEVA PI Web API Connector
=========================================
Pulls real-time and historical SCADA/process data from
OSIsoft PI Server via the PI Web API (AVEVA PI System).

Supports:
  - PI Web API 2019+
  - PI Data Archive (real-time streaming + historical)
  - PI Asset Framework (AF) for asset hierarchy

Required environment variables:
  - PI_WEBAPI_URL      e.g., https://pi-server.yourcompany.com/piwebapi
  - PI_USERNAME        Service account (read-only is sufficient)
  - PI_PASSWORD
  OR
  - PI_CLIENT_CERT     Path to client certificate (mutual TLS)
  - PI_CLIENT_KEY      Path to client private key

OT Security Note:
  PI Web API runs in the DMZ. Never expose PI directly to internet.
  Use a dedicated OT gateway with data diode for ingestion.
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

import requests
from requests.auth import HTTPBasicAuth
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("SAHARYN_PI_WEBAPI")

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
PI_WEBAPI_URL  = os.getenv("PI_WEBAPI_URL")
PI_USERNAME    = os.getenv("PI_USERNAME")
PI_PASSWORD    = os.getenv("PI_PASSWORD")
PI_CLIENT_CERT = os.getenv("PI_CLIENT_CERT")
PI_CLIENT_KEY  = os.getenv("PI_CLIENT_KEY")

# PI tag → SAHARYN feature mapping
# Key:   PI tag path in the server
# Value: SAHARYN field name
PI_TAG_MAP: Dict[str, Dict] = {
    r"\\PISERVER\SA_EAST_RU_01.PUMP_RU_42.Vibration":      {"asset_id": "PUMP_RU_42",   "field": "vibration_mm_s"},
    r"\\PISERVER\SA_EAST_RU_01.PUMP_RU_42.BearingTemp":    {"asset_id": "PUMP_RU_42",   "field": "bearing_temp_c"},
    r"\\PISERVER\SA_EAST_RU_01.PUMP_RU_42.FlowRate":       {"asset_id": "PUMP_RU_42",   "field": "flow_rate_m3_h"},
    r"\\PISERVER\SA_EAST_RU_01.PUMP_RU_42.InletPressure":  {"asset_id": "PUMP_RU_42",   "field": "inlet_pressure_bar"},
    r"\\PISERVER\SA_EAST_RU_01.PUMP_RU_42.Power":          {"asset_id": "PUMP_RU_42",   "field": "power_consumption_kw"},
    r"\\PISERVER\SA_EAST_RU_01.COMP_RU_01.Vibration":      {"asset_id": "COMP_RU_01",   "field": "vibration_mm_s"},
    r"\\PISERVER\SA_EAST_RU_01.COMP_RU_01.OutletPressure": {"asset_id": "COMP_RU_01",   "field": "outlet_pressure_bar"},
    r"\\PISERVER\SA_EAST_RU_01.COMP_RU_01.Power":          {"asset_id": "COMP_RU_01",   "field": "power_consumption_kw"},
}


class PIWebAPIConnector:
    """
    Reads process historian data from AVEVA PI Server
    through the PI Web API (REST interface).
    """

    def __init__(self):
        self._available = False
        self._tag_webids: Dict[str, str] = {}   # Cache: tag path → WebID
        self.session = requests.Session()
        # Demo/Simulation State
        self.atmospheric_stress = 0.1 # Default clear sky
        self._connect()

    def set_simulation_stress(self, aod: float):
        """Dynamic multiplier for demo scenarios. Connects AOD to mechanical response."""
        self.atmospheric_stress = aod

    def _connect(self):
        """Initialize PI Web API session."""
        if not PI_WEBAPI_URL or "dummy" in PI_WEBAPI_URL.lower():
            logger.warning("PI_WEBAPI_URL not set or DUMMY. Maintaining SIMULATION_MODE.")
            self._available = False
            return

        # Configure authentication
        if PI_CLIENT_CERT and PI_CLIENT_KEY:
            self.session.cert = (PI_CLIENT_CERT, PI_CLIENT_KEY)
            auth_method = "CLIENT_CERT"
        elif PI_USERNAME and PI_PASSWORD:
            self.session.auth = HTTPBasicAuth(PI_USERNAME, PI_PASSWORD)
            auth_method = "KERBEROS_BASIC"
        else:
            logger.warning("No PI credentials configured.")
            return

        # Disable SSL verification for self-signed PI certs in OT networks
        # In production: add the PI CA certificate instead
        self.session.verify = False
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        })

        # Test connection
        try:
            resp = self.session.get(f"{PI_WEBAPI_URL}/system", timeout=10)
            resp.raise_for_status()
            server_info = resp.json()
            logger.info(
                f"PI Web API connected: {PI_WEBAPI_URL} "
                f"auth={auth_method} "
                f"version={server_info.get('ProductVersion', 'unknown')}"
            )
            self._available = True
            # Pre-load WebIDs for configured tags
            self._preload_webids()
        except Exception as e:
            logger.warning(f"PI Web API connection failed: {e}")

    def _preload_webids(self):
        """Cache WebIDs for all configured PI tags."""
        for tag_path in PI_TAG_MAP:
            webid = self._resolve_webid(tag_path)
            if webid:
                self._tag_webids[tag_path] = webid

        logger.info(f"PI: Resolved {len(self._tag_webids)}/{len(PI_TAG_MAP)} tag WebIDs")

    def _resolve_webid(self, tag_path: str) -> Optional[str]:
        """Resolve a PI tag path to a WebID (PI API's unique identifier)."""
        try:
            resp = self.session.get(
                f"{PI_WEBAPI_URL}/points",
                params={"path": tag_path},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("WebId")
        except Exception as e:
            logger.warning(f"Could not resolve WebID for {tag_path}: {e}")
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
    def _get(self, endpoint: str, params: Dict = None) -> Any:
        """Authenticated GET to PI Web API."""
        url = urljoin(PI_WEBAPI_URL + "/", endpoint)
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_current_value(self, tag_path: str) -> Optional[Dict]:
        """
        Fetch the most recent value for a PI tag.
        Supports REAL mode (PI Web API) and SIMULATION mode.
        """
        if not self._available:
            return self._generate_simulated_value(tag_path)

        webid = self._tag_webids.get(tag_path) or self._resolve_webid(tag_path)
        if not webid:
            logger.error(f"PI: Cannot resolve WebID for {tag_path}")
            return self._generate_simulated_value(tag_path)

        try:
            data = self._get(f"streams/{webid}/value")
            return {
                "tag":       tag_path,
                "value":     data.get("Value"),
                "timestamp": data.get("Timestamp"),
                "quality":   data.get("Good", False),
                "units":     data.get("UnitsAbbreviation", ""),
            }
        except Exception as e:
            logger.error(f"PI get_current_value failed for {tag_path}: {e}")
            return self._generate_simulated_value(tag_path)

    def _generate_simulated_value(self, tag_path: str) -> Dict:
        """Generates physics-aligned synthetic telemetry for testing."""
        import random
        import numpy as np
        
        # Scaling factor: Stress (AOD) causes increase in deviation
        stress = self.atmospheric_stress
        val = 0.0
        tag_upper = tag_path.upper()
        
        if "VIB" in tag_upper:
            # ISO 10816 / 20816 Calibration: 
            # Normal: <1.5, Early: 2-3, Inspection: 3-5, High: 5-7, Critical: 7-10, Shutdown: >10
            # AOD stress increases exponentially to map directly to these thresholds
            base_vib = 1.2
            clog_impact = (stress ** 2) * 12.0 # 0.95 AOD -> 10.8mm/s, 0.5 AOD -> 4.2mm/s, 0.1 AOD -> 1.32mm/s
            val = base_vib + clog_impact + np.random.normal(0, 0.3)
        elif "TEMP" in tag_upper:
            # Temperature rises as cooling efficiency drops
            val = 65.0 + (stress * 20.0) + np.random.normal(0, 5.0)
        elif "INLET" in tag_upper:
            # Inlet pressure drops as filter clogs
            val = max(0.1, 4.5 - (stress * 3.0) + np.random.normal(0, 0.2))
        elif "OUTLET" in tag_upper:
            # Outlet pressure might drop or oscillate during surge
            val = 8.5 - (stress * 1.5) + np.random.normal(0, 0.5)
        elif "POWER" in tag_upper:
            # Power consumption spikes as engine works harder against clogging
            val = 120.0 + (stress * 50.0) + np.random.normal(0, 10.0)
        else:
            val = random.uniform(10, 100)
            
        return {
            "tag": tag_path,
            "value": round(val, 4),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "quality": True,
            "units": "SIM"
        }

    def get_recorded_data(
        self,
        tag_path: str,
        start: datetime,
        end: datetime,
        interval: str = "1m",
        max_entries: int = 1440,
    ) -> List[Dict]:
        """
        Fetch interpolated historical data at fixed intervals.

        Args:
            tag_path:   PI tag path
            start, end: Time range
            interval:   Sampling interval ('1m', '5m', '1h', etc.)
            max_entries: Maximum number of samples

        Returns:
            List of {timestamp, value, quality} dicts
        """
        if not self._available:
            return []

        webid = self._tag_webids.get(tag_path) or self._resolve_webid(tag_path)
        if not webid:
            return []

        try:
            data = self._get(
                f"streams/{webid}/interpolated",
                params={
                    "startTime":    start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "endTime":      end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "interval":     interval,
                    "maxCount":     max_entries,
                    "selectedFields": "Items.Timestamp;Items.Value;Items.Good",
                },
            )
            items = data.get("Items", [])
            return [
                {
                    "timestamp": item.get("Timestamp"),
                    "value":     item.get("Value"),
                    "quality":   192 if item.get("Good") else 0,  # OPC-UA quality code
                }
                for item in items
                if item.get("Value") is not None
            ]
        except Exception as e:
            logger.error(f"PI get_recorded_data failed: {e}")
            return []

    def get_all_assets_snapshot(self) -> Dict[str, Dict]:
        """
        Fetch current values for all configured PI tags.
        Returns dict: asset_id → {field: value}
        """
        if not self._available:
            return {}

        snapshot: Dict[str, Dict] = {}

        for tag_path, mapping in PI_TAG_MAP.items():
            result = self.get_current_value(tag_path)
            if result and result.get("quality"):
                asset_id = mapping["asset_id"]
                field    = mapping["field"]
                if asset_id not in snapshot:
                    snapshot[asset_id] = {}
                snapshot[asset_id][field] = result["value"]

        logger.info(f"PI snapshot: {len(snapshot)} assets updated")
        return snapshot

    def validate_connection(self) -> Dict:
        """Health check for PI Web API connectivity."""
        return {
            "status": "CONNECTED" if self._available else "DISCONNECTED",
            "base_url": PI_WEBAPI_URL,
            "tags_configured": len(PI_TAG_MAP),
            "webids_cached": len(self._tag_webids),
        }
