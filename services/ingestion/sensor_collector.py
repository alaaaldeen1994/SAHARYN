import time
import json
import logging
import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Dict, Optional

from apps.ingestion.scada.pi_webapi_connector import PIWebAPIConnector
from core.database.session import SessionLocal
from core.database.models import SensorTelemetry, SatelliteTelemetry
from services.ai_core.causal_engine import CausalIntegrityManifold
from dotenv import load_dotenv
load_dotenv()

# --- CONFIGURATION ---
MAPPING_PATH = "config/pilot_tag_mapping.json"
logger = logging.getLogger("SAHARYN_SENSOR_COLLECTOR")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s")

class SensorCollectorService:
    """
    Orchestrates industrial asset telemetry ingestion.
    Supports multi-rate sampling and TimescaleDB persistence.
    """
    
    def __init__(self):
        self.connector = PIWebAPIConnector()
        self.manifold = CausalIntegrityManifold()
        self.config = self._load_config()
        self.last_poll_times: Dict[str, float] = {}
        self.site_id = self.config.get("site_id", "UNKNOWN_SITE")
        self.asset_id = self.config.get("asset_id", "UNKNOWN_ASSET")
        
        # Performance & Reliability Metrics
        self.ingestion_count = 0
        self.last_sync_drift = 0.0
        self.cached_aod = 0.1 # Default clear sky

    def _sync_environmental_force(self):
        """Fetches latest real AOD from DB to drive simulated mechanical response."""
        try:
            db = SessionLocal()
            latest_sat = db.query(SatelliteTelemetry).order_by(SatelliteTelemetry.timestamp.desc()).first()
            if latest_sat:
                self.cached_aod = latest_sat.aod_550nm
                # Feed to connector to scale synthetic data
                self.connector.set_simulation_stress(self.cached_aod)
                logger.debug(f"ENV_SYNC: Scaling simulation with AOD={self.cached_aod:.4f}")
            db.close()
        except Exception as e:
            logger.warning(f"ENV_SYNC_FAILURE: {e}")

    def _load_config(self) -> Dict:
        try:
            with open(MAPPING_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"CONFIG_FAILURE: Could not load mapping: {e}")
            return {"mappings": []}

    def _generate_integrity_hash(self, payload: str) -> str:
        return hashlib.sha256(payload.encode()).hexdigest()

    async def poll_tag(self, mapping: Dict):
        """Fetches a single tag and persists to DB."""
        tag_path = mapping["pi_tag"]
        field = mapping["internal_field"]
        
        # 0. SYNC WITH REAL WORLD (if simulation mode)
        if not self.connector._available:
            self._sync_environmental_force()

        # 1. FETCH
        logger.debug(f"POLLING: {tag_path}")
        result = self.connector.get_current_value(tag_path)
        
        # 2. DATA QUALITY CHECK
        if not result or not result.get("quality"):
            logger.warning(f"QUALITY_BAD: Tag={tag_path} | Quality=0")
            # In a real pilot, we record the bad quality row too
            self._write_to_db(mapping, 0.0, "0")
            return

        # 3. TIME SYNC CHECK
        pi_time_str = result.get("timestamp")
        try:
            pi_time = datetime.fromisoformat(pi_time_str.replace("Z", "+00:00"))
            local_now = datetime.now(timezone.utc)
            drift = (local_now - pi_time).total_seconds()
            if abs(drift) > 1.0:
                logger.warning(f"TIME_DRIFT: Site={self.site_id} | Drift={drift:.2f}s")
                self.last_sync_drift = drift
        except Exception as e:
            logger.error(f"TIMESTAMP_PARSE_FAIL: {e}")
            pi_time = datetime.now(timezone.utc)

        # 4. LOAD & CACHE
        value = float(result.get("value", 0.0))
        self._write_to_db(mapping, value, "192", pi_time)
        self.last_poll_times[f"val_{field}"] = value # Cache latest value for fusion
        
        # 5. SYSTEM FUSION: Trigger manifold when vibration is updated (the 1Hz ticker)
        if field == "vibration_mm_s":
            # Assemble current telemetry snapshot
            telemetry_snapshot = {
                "vibration": value,
                "inlet_pressure_bar": self.last_poll_times.get("val_inlet_pressure_bar", 4.5),
                "outlet_pressure_bar": self.last_poll_times.get("val_outlet_pressure_bar", 8.5),
                "bearing_temp_c": self.last_poll_times.get("val_bearing_temp_c", 65.0),
                "power_kw": self.last_poll_times.get("val_power_kw", 120.0),
                "wind_speed": 10.0 # Will be fused from Satellite feed in Phase 3
            }
            # Execute Causal Inference
            # We assume a baseline AOD of 0.5 for diagnostic logging
            self.manifold.calculate_propagation_matrix(0.5, telemetry_snapshot)
            logger.info(
                f"FUSION_DIAGNOSTIC: Asset={self.asset_id} | Vib={value:.2f} | "
                f"dP={abs(telemetry_snapshot['outlet_pressure_bar'] - telemetry_snapshot['inlet_pressure_bar']):.2f} | "
                f"Stability={self.manifold.global_stability_index:.4f}"
            )

    def _write_to_db(self, mapping: Dict, value: float, quality: str, timestamp: Optional[datetime] = None):
        try:
            ts = timestamp or datetime.now(timezone.utc)
            db = SessionLocal()
            payload = f"{self.asset_id}:{mapping['pi_tag']}:{value}:{ts.isoformat()}"
            
            entry = SensorTelemetry(
                site_id=self.site_id,
                asset_id=self.asset_id,
                timestamp=ts,
                source_tag=mapping["pi_tag"],
                value=value,
                unit=mapping.get("unit"),
                quality_code=quality,
                integrity_hash=self._generate_integrity_hash(payload)
            )
            db.add(entry)
            db.commit()
            db.close()
            self.ingestion_count += 1
        except Exception as e:
            logger.error(f"DB_LOAD_FAILURE: {e}")

    async def run_lifecycle(self):
        """Main execution loop managing multi-rate polling."""
        logger.info(f"SENSOR_COLLECTOR: Starting Pilot Cycle for {self.asset_id} at {self.site_id}")
        
        while True:
            now = time.time()
            tasks = []
            
            for m in self.config["mappings"]:
                tag = m["pi_tag"]
                rate = 1.0 / m["sampling_rate_hz"] # Interval in seconds
                
                last_poll = self.last_poll_times.get(tag, 0)
                if now - last_poll >= rate:
                    tasks.append(self.poll_tag(m))
                    self.last_poll_times[tag] = now
            
            if tasks:
                await asyncio.gather(*tasks)
            
            # Watchdog: Alert if no data for 2 mins (not implemented here but logic ready)
            
            await asyncio.sleep(0.1) # High-resolution ticker

if __name__ == "__main__":
    collector = SensorCollectorService()
    try:
        asyncio.run(collector.run_lifecycle())
    except KeyboardInterrupt:
        logger.info("COLLECTOR_SHUTDOWN: Operational SIGINT perceived.")
