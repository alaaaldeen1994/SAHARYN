"""
SAHARYN AI — IBM Maximo CMMS Connector
========================================
Fetches work orders, maintenance logs, failure records,
and equipment data from IBM Maximo Asset Management.

Supports:
  - Maximo REST API (v7.6+)
  - Maximo Application Framework (MAF)

Auth:
  - API Key (preferred)
  - Basic Auth (legacy)

Required environment variables:
  - MAXIMO_BASE_URL    e.g., https://maximo.yourcompany.com
  - MAXIMO_API_KEY     OR
  - MAXIMO_USERNAME + MAXIMO_PASSWORD

Asset ID normalization:
  Maximo asset numbers → SAHARYN asset IDs
  e.g., MAXIMO:AX-PRX-00042 → PUMP_RU_42
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("SAHARYN_MAXIMO")

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
MAXIMO_BASE_URL = os.getenv("MAXIMO_BASE_URL")
MAXIMO_API_KEY  = os.getenv("MAXIMO_API_KEY")
MAXIMO_USERNAME = os.getenv("MAXIMO_USERNAME")
MAXIMO_PASSWORD = os.getenv("MAXIMO_PASSWORD")

# Asset ID mapping: Maximo assetnum → SAHARYN asset_id
# Populate this from your Maximo system's asset register
ASSET_ID_MAP: Dict[str, str] = {
    "AX-PRX-00042": "PUMP_RU_42",
    "AX-CMP-00001": "COMP_RU_01",
    "AX-FLT-00007": "FILTER_RU_07",
    "AX-HEX-00003": "HEX_RU_03",
    "AX-RTR-00001": "ROTOR_NEOM_01",
}


class MaximoConnector:
    """
    Fetches CMMS data from IBM Maximo for maintenance history
    and work order integration with the SAHARYN AI pipeline.
    """

    def __init__(self):
        self._available = False
        self.session = requests.Session()
        self._connect()

    def _connect(self):
        """Initialize Maximo connection with API key or basic auth."""
        if not MAXIMO_BASE_URL:
            logger.warning("MAXIMO_BASE_URL not set. Maximo connector disabled.")
            return

        if MAXIMO_API_KEY:
            self.session.headers.update({
                "apikey": MAXIMO_API_KEY,
                "Accept": "application/json",
                "Content-Type": "application/json",
            })
            auth_method = "API_KEY"
        elif MAXIMO_USERNAME and MAXIMO_PASSWORD:
            self.session.auth = (MAXIMO_USERNAME, MAXIMO_PASSWORD)
            auth_method = "BASIC_AUTH"
        else:
            logger.warning("No Maximo credentials found. Set MAXIMO_API_KEY.")
            return

        # Test connection
        try:
            resp = self.session.get(
                f"{MAXIMO_BASE_URL}/maximo/oslc/os/mxasset",
                params={"oslc.maxItems": 1, "lean": 1},
                timeout=10,
            )
            resp.raise_for_status()
            self._available = True
            logger.info(f"Maximo connected: {MAXIMO_BASE_URL} auth={auth_method}")
        except Exception as e:
            logger.warning(f"Maximo connection test failed: {e}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        """Authenticated GET request to Maximo OSLC API."""
        url = f"{MAXIMO_BASE_URL}/maximo/oslc/os/{endpoint}"
        params = params or {}
        params["lean"] = 1   # Lean mode: minimal JSON, no namespaces
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

    def normalize_asset_id(self, maximo_assetnum: str) -> str:
        """
        Convert Maximo asset number to SAHARYN asset_id.
        Falls back to prefixed Maximo ID if not in mapping.
        """
        saharyn_id = ASSET_ID_MAP.get(maximo_assetnum)
        if not saharyn_id:
            logger.warning(
                f"Asset {maximo_assetnum} not in ASSET_ID_MAP. "
                f"Add it to apps/ingestion/cmms/maximo_connector.py"
            )
            saharyn_id = f"MAXIMO:{maximo_assetnum}"
        return saharyn_id

    def get_work_orders(
        self,
        site_id: Optional[str] = None,
        asset_id: Optional[str] = None,
        status: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Fetch work orders from Maximo with optional filters.

        Args:
            site_id:  Maximo site ID (e.g., "RIYADH")
            asset_id: Maximo asset number (e.g., "AX-PRX-00042")
            status:   Work order status filter (e.g., "COMP", "WAPPR", "INPRG")
            since:    Fetch orders changed after this date
            limit:    Max results

        Returns:
            Normalized list of work orders with SAHARYN asset IDs
        """
        if not self._available:
            logger.warning("Maximo unavailable — returning empty work orders list")
            return []

        # Build OSLC where clause
        where_clauses = []
        if site_id:
            where_clauses.append(f'siteid="{site_id}"')
        if asset_id:
            where_clauses.append(f'assetnum="{asset_id}"')
        if status:
            where_clauses.append(f'status="{status}"')
        if since:
            where_clauses.append(f'changedate>"{since.strftime("%Y-%m-%dT%H:%M:%S+00:00")}"')

        params = {
            "oslc.select": "wonum,description,assetnum,siteid,status,worktype,"
                           "estdur,actdur,actlabcost,actmatcost,reportdate,changedate,"
                           "wopriority,failurecode,jpnum",
            "oslc.maxItems": limit,
            "oslc.orderBy": "-changedate",
        }
        if where_clauses:
            params["oslc.where"] = " and ".join(where_clauses)

        try:
            response = self._get("mxwo", params=params)
            raw_orders = response.get("member", [])

            # Normalize to SAHARYN schema
            normalized = []
            for wo in raw_orders:
                normalized.append({
                    "work_order_id":        wo.get("wonum"),
                    "asset_id":             self.normalize_asset_id(wo.get("assetnum", "")),
                    "maximo_assetnum":      wo.get("assetnum"),
                    "site_id":              wo.get("siteid"),
                    "description":          wo.get("description"),
                    "work_type":            wo.get("worktype"),     # PM, CM, EM (preventive/corrective/emergency)
                    "status":               wo.get("status"),
                    "priority":             wo.get("wopriority"),
                    "failure_code":         wo.get("failurecode"),
                    "estimated_hours":      wo.get("estdur"),
                    "actual_hours":         wo.get("actdur"),
                    "labor_cost_usd":       wo.get("actlabcost"),
                    "material_cost_usd":    wo.get("actmatcost"),
                    "reported_date":        wo.get("reportdate"),
                    "modified_date":        wo.get("changedate"),
                    "job_plan_id":          wo.get("jpnum"),
                    "source":               "IBM_MAXIMO",
                })

            logger.info(f"Maximo: fetched {len(normalized)} work orders")
            return normalized

        except Exception as e:
            logger.error(f"Maximo work orders fetch failed: {e}")
            return []

    def get_failure_history(
        self,
        asset_id: str,
        lookback_days: int = 365,
    ) -> List[Dict]:
        """
        Fetch failure and breakdown history for a specific asset.
        Used to build asset reliability profiles for the AI models.
        """
        if not self._available:
            return []

        since = datetime.utcnow() - timedelta(days=lookback_days)
        return self.get_work_orders(
            asset_id=asset_id,
            status="COMP",       # Completed work orders only
            since=since,
            limit=500,
        )

    def get_filter_schedules(self, site_id: Optional[str] = None) -> List[Dict]:
        """
        Fetch upcoming filter replacement schedules.
        Critical for SAHARYN's dust impact predictions.
        """
        if not self._available:
            return []

        params = {
            "oslc.where": 'worktype="PM" and jpnum like "FILTER%"',
            "oslc.select": "wonum,assetnum,siteid,schedstart,schedfinish,status",
            "oslc.maxItems": 200,
        }
        if site_id:
            params["oslc.where"] += f' and siteid="{site_id}"'

        try:
            response = self._get("mxwo", params=params)
            schedules = []
            for item in response.get("member", []):
                schedules.append({
                    "work_order_id":     item.get("wonum"),
                    "asset_id":          self.normalize_asset_id(item.get("assetnum", "")),
                    "scheduled_start":   item.get("schedstart"),
                    "scheduled_finish":  item.get("schedfinish"),
                    "status":            item.get("status"),
                    "type":              "FILTER_REPLACEMENT",
                    "source":            "IBM_MAXIMO",
                })
            return schedules
        except Exception as e:
            logger.error(f"Maximo filter schedules fetch failed: {e}")
            return []

    def validate_connection(self) -> Dict:
        """Health check for Maximo connectivity."""
        return {
            "status": "CONNECTED" if self._available else "DISCONNECTED",
            "base_url": MAXIMO_BASE_URL,
            "auth_method": "API_KEY" if MAXIMO_API_KEY else ("BASIC_AUTH" if MAXIMO_USERNAME else "NONE"),
            "asset_mappings": len(ASSET_ID_MAP),
        }
