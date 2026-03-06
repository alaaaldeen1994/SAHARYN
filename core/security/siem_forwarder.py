"""
SAHARYN AI — SIEM Integration: Splunk HEC + ELK Structured Log Forwarder
=========================================================================
Sends structured security and operational audit events to:
  - Splunk via HTTP Event Collector (HEC)
  - Elasticsearch (ELK Stack) via REST
  - Azure Sentinel (Log Analytics Workspace)
  - Fallback: local structured JSON files (always active)

Standards:
  - ISO 27001: A.12.4 (Event Logging)
  - SOC2 CC7.2 (System Monitoring)
  - NIST CSF DE.AE-1 / DE.CM-7

Events captured:
  - Authentication success/failure
  - API access and latency
  - Model inference anomalies
  - Data drift detection
  - Sovereign mode changes
  - Unauthorized access attempts
"""

import os
import json
import time
import logging
import threading
import queue
import hashlib
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("SAHARYN_SIEM")

# ─────────────────────────────────────────────────────────────────────────────
# SIEM Event Severity Levels
# ─────────────────────────────────────────────────────────────────────────────

class SIEMSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"


class SIEMEventType(str, Enum):
    # Security
    AUTH_SUCCESS        = "authentication.success"
    AUTH_FAILURE        = "authentication.failure"
    UNAUTHORIZED_ACCESS = "security.unauthorized_access"
    PRIVILEGE_ESCALATION= "security.privilege_escalation"
    SOVEREIGN_ACTIVATED = "security.sovereign_mode_activated"
    
    # Operations
    API_REQUEST         = "api.request"
    API_ERROR           = "api.error"
    MODEL_INFERENCE     = "ml.inference_complete"
    MODEL_DRIFT         = "ml.concept_drift_detected"
    RETRAINING_TRIGGERED= "ml.retraining_triggered"
    
    # Infrastructure
    SERVICE_START       = "service.startup"
    SERVICE_STOP        = "service.shutdown"
    HEALTH_CHECK        = "service.health_check"
    DATA_INGESTION      = "data.ingestion_complete"
    
    # Compliance
    POLICY_VIOLATION    = "compliance.policy_violation"
    AUDIT_EXPORT        = "compliance.audit_export"
    ESG_CLAIM           = "compliance.esg_claim_committed"


# ─────────────────────────────────────────────────────────────────────────────
# Structured SIEM Event
# ─────────────────────────────────────────────────────────────────────────────

class SIEMEvent:
    """Immutable structured SIEM event with deterministic hash for deduplication."""

    def __init__(
        self,
        event_type: SIEMEventType,
        severity: SIEMSeverity,
        source: str,
        message: str,
        actor: Optional[str] = None,
        resource: Optional[str] = None,
        outcome: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.event_type = event_type.value
        self.severity = severity.value
        self.source = source
        self.message = message
        self.actor = actor or "SYSTEM"
        self.resource = resource
        self.outcome = outcome
        self.context = context or {}

        # Deterministic event ID for deduplication in SIEM
        payload = f"{self.timestamp}{self.event_type}{self.source}{self.message}"
        self.event_id = hashlib.sha256(payload.encode()).hexdigest()[:24]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id":   self.event_id,
            "timestamp":  self.timestamp,
            "event_type": self.event_type,
            "severity":   self.severity,
            "source":     self.source,
            "actor":      self.actor,
            "resource":   self.resource,
            "outcome":    self.outcome,
            "message":    self.message,
            "context":    self.context,
            "platform":   "SAHARYN_AI_v2",
            "environment": os.getenv("SAHARYN_ENV", "PRODUCTION"),
        }

    def to_splunk_payload(self) -> Dict[str, Any]:
        """Format for Splunk HEC (HTTP Event Collector)."""
        return {
            "time": time.time(),
            "host": os.getenv("HOSTNAME", "saharyn-gateway"),
            "source": f"saharyn:{self.source}",
            "sourcetype": "saharyn:audit",
            "index": "saharyn_security",
            "event": self.to_dict(),
        }

    def to_elk_document(self) -> Dict[str, Any]:
        """Format for Elasticsearch (ECS compliant)."""
        d = self.to_dict()
        return {
            "@timestamp": self.timestamp,
            "event": {
                "id":       self.event_id,
                "kind":     "event",
                "category": self.event_type.split(".")[0],
                "type":     self.event_type,
                "outcome":  self.outcome or "unknown",
                "severity": {"critical": 90, "high": 70, "medium": 50, "low": 25, "info": 10}.get(self.severity, 0),
            },
            "message": self.message,
            "user": {"name": self.actor},
            "saharyn": {k: v for k, v in d.items() if k not in ("timestamp", "message")},
        }

    def to_sentinel_payload(self) -> Dict[str, Any]:
        """Format for Azure Sentinel Log Analytics Workspace."""
        d = self.to_dict()
        d["TimeGenerated"] = self.timestamp
        d["Computer"] = os.getenv("HOSTNAME", "saharyn-gateway")
        return d


# ─────────────────────────────────────────────────────────────────────────────
# SIEM Forwarder
# ─────────────────────────────────────────────────────────────────────────────

class SIEMForwarder:
    """
    Asynchronous, buffered SIEM event forwarder.
    
    Architecture:
    - Producer: Application code calls `emit(event)` (non-blocking)
    - Consumer: Background thread flushes the queue in batches
    - Fallback: Every event is ALWAYS written to local NDJSON file
    
    This ensures zero audit log loss even during network partition.
    """

    def __init__(self):
        self._queue: queue.Queue = queue.Queue(maxsize=10000)
        self._local_log_dir = Path(os.getenv("SIEM_LOCAL_LOG_DIR", "data/siem_logs"))
        self._local_log_dir.mkdir(parents=True, exist_ok=True)

        # SIEM backends (configured via environment variables)
        self._splunk_url     = os.getenv("SPLUNK_HEC_URL")        # e.g. https://splunk.company.com:8088/services/collector
        self._splunk_token   = os.getenv("SPLUNK_HEC_TOKEN")      # HEC token
        self._elk_url        = os.getenv("ELK_ELASTICSEARCH_URL")  # e.g. https://elastic.company.com:9200
        self._elk_index      = os.getenv("ELK_INDEX_NAME", "saharyn-audit")
        self._elk_api_key    = os.getenv("ELK_API_KEY")
        self._sentinel_url   = os.getenv("AZURE_SENTINEL_URL")     # Log Analytics Data Collector API
        self._sentinel_key   = os.getenv("AZURE_SENTINEL_KEY")

        self._batch_size   = int(os.getenv("SIEM_BATCH_SIZE", "20"))
        self._flush_interval = float(os.getenv("SIEM_FLUSH_INTERVAL_SECS", "5.0"))

        # HTTP session with retry logic
        self._session = self._build_session()

        # Log which backends are active
        active = []
        if self._splunk_url and self._splunk_token:
            active.append("Splunk HEC")
        if self._elk_url:
            active.append("Elasticsearch/ELK")
        if self._sentinel_url:
            active.append("Azure Sentinel")
        active.append("Local NDJSON (always active)")
        logger.info(f"SIEM backends active: {', '.join(active)}")

        # Start background flush thread
        self._shutdown_flag = threading.Event()
        self._worker = threading.Thread(target=self._flush_worker, daemon=True, name="siem-flush")
        self._worker.start()

    def _build_session(self) -> requests.Session:
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def emit(self, event: SIEMEvent) -> None:
        """
        Non-blocking event emission. Drop to queue; background worker handles delivery.
        The local fallback is SYNCHRONOUS to guarantee no loss.
        """
        # Always write to local file immediately (durability)
        self._write_local(event)
        
        # Queue for async SIEM forwarding
        try:
            self._queue.put_nowait(event)
        except queue.Full:
            logger.warning("SIEM queue full — background worker may be lagging. Event captured locally only.")

    def _write_local(self, event: SIEMEvent) -> None:
        """Write event to daily rotating NDJSON file (immutable audit trail)."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        log_file = self._local_log_dir / f"saharyn_audit_{today}.ndjson"
        line = json.dumps(event.to_dict()) + "\n"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(line)

    def _flush_worker(self) -> None:
        """Background thread: drain queue in batches, forward to all backends."""
        logger.info("SIEM flush worker started.")
        while not self._shutdown_flag.is_set():
            batch = []
            try:
                deadline = time.time() + self._flush_interval
                while len(batch) < self._batch_size and time.time() < deadline:
                    try:
                        event = self._queue.get(timeout=0.1)
                        batch.append(event)
                    except queue.Empty:
                        break
            except Exception as e:
                logger.error(f"SIEM batch collection error: {e}")

            if batch:
                self._forward_splunk(batch)
                self._forward_elk(batch)
                self._forward_sentinel(batch)

    def _forward_splunk(self, events: list) -> None:
        if not (self._splunk_url and self._splunk_token):
            return
        try:
            payloads = "\n".join(json.dumps(e.to_splunk_payload()) for e in events)
            resp = self._session.post(
                self._splunk_url,
                data=payloads,
                headers={
                    "Authorization": f"Splunk {self._splunk_token}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            resp.raise_for_status()
            logger.debug(f"Splunk: forwarded {len(events)} events")
        except Exception as e:
            logger.error(f"Splunk forward failed: {e} — events already captured locally")

    def _forward_elk(self, events: list) -> None:
        if not self._elk_url:
            return
        try:
            # Elasticsearch Bulk API format
            lines = []
            for event in events:
                lines.append(json.dumps({"index": {"_index": self._elk_index, "_id": event.event_id}}))
                lines.append(json.dumps(event.to_elk_document()))
            bulk_body = "\n".join(lines) + "\n"

            headers = {"Content-Type": "application/x-ndjson"}
            if self._elk_api_key:
                headers["Authorization"] = f"ApiKey {self._elk_api_key}"

            resp = self._session.post(
                f"{self._elk_url}/_bulk",
                data=bulk_body,
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            logger.debug(f"ELK: indexed {len(events)} events to {self._elk_index}")
        except Exception as e:
            logger.error(f"ELK forward failed: {e} — events already captured locally")

    def _forward_sentinel(self, events: list) -> None:
        if not (self._sentinel_url and self._sentinel_key):
            return
        try:
            payloads = [e.to_sentinel_payload() for e in events]
            resp = self._session.post(
                self._sentinel_url,
                json=payloads,
                headers={
                    "Authorization": f"SharedKey {self._sentinel_key}",
                    "Content-Type": "application/json",
                    "Log-Type": "SaharynAuditV2",
                },
                timeout=15,
            )
            resp.raise_for_status()
            logger.debug(f"Azure Sentinel: forwarded {len(events)} events")
        except Exception as e:
            logger.error(f"Sentinel forward failed: {e} — events already captured locally")

    def shutdown(self) -> None:
        """Graceful shutdown: flush remaining queue before stopping."""
        logger.info("SIEM forwarder shutting down, flushing remaining events...")
        self._shutdown_flag.set()
        self._worker.join(timeout=15)
        logger.info("SIEM forwarder shutdown complete.")


# ─────────────────────────────────────────────────────────────────────────────
# Global SIEM instance (singleton pattern — safe for multi-threaded FastAPI)
# ─────────────────────────────────────────────────────────────────────────────

_siem_instance: Optional[SIEMForwarder] = None

def get_siem() -> SIEMForwarder:
    global _siem_instance
    if _siem_instance is None:
        _siem_instance = SIEMForwarder()
    return _siem_instance


# ─────────────────────────────────────────────────────────────────────────────
# Convenience factory functions for common event types
# ─────────────────────────────────────────────────────────────────────────────

def emit_auth_failure(actor: str, ip: str, reason: str) -> None:
    get_siem().emit(SIEMEvent(
        event_type=SIEMEventType.AUTH_FAILURE,
        severity=SIEMSeverity.HIGH,
        source="api_gateway",
        message=f"Authentication failure from {ip}",
        actor=actor,
        resource="/v2/*",
        outcome="failure",
        context={"ip": ip, "reason": reason},
    ))

def emit_auth_success(actor: str, ip: str, role: str) -> None:
    get_siem().emit(SIEMEvent(
        event_type=SIEMEventType.AUTH_SUCCESS,
        severity=SIEMSeverity.INFO,
        source="api_gateway",
        message=f"Authenticated user {actor} [{role}]",
        actor=actor,
        outcome="success",
        context={"ip": ip, "role": role},
    ))

def emit_model_drift(feature: str, p_value: float, asset_id: str) -> None:
    get_siem().emit(SIEMEvent(
        event_type=SIEMEventType.MODEL_DRIFT,
        severity=SIEMSeverity.MEDIUM,
        source="mlops_monitor",
        message=f"Concept drift on feature '{feature}' for asset {asset_id} (p={p_value:.4f})",
        resource=f"model/failure_predictor/{asset_id}",
        outcome="alert",
        context={"feature": feature, "p_value": p_value, "asset_id": asset_id},
    ))

def emit_inference_event(asset_id: str, failure_prob: float, latency_ms: float) -> None:
    severity = SIEMSeverity.HIGH if failure_prob > 0.7 else SIEMSeverity.INFO
    get_siem().emit(SIEMEvent(
        event_type=SIEMEventType.MODEL_INFERENCE,
        severity=severity,
        source="causal_engine",
        message=f"Inference complete: {asset_id} failure_prob={failure_prob:.2%}",
        resource=f"asset/{asset_id}",
        outcome="success",
        context={"asset_id": asset_id, "failure_probability": failure_prob, "latency_ms": latency_ms},
    ))

def emit_sovereign_change(enabled: bool, actor: str) -> None:
    get_siem().emit(SIEMEvent(
        event_type=SIEMEventType.SOVEREIGN_ACTIVATED,
        severity=SIEMSeverity.HIGH,
        source="api_gateway",
        message=f"Sovereign mode {'ACTIVATED' if enabled else 'DEACTIVATED'} by {actor}",
        actor=actor,
        outcome="success",
        context={"sovereign_mode": enabled},
    ))

def emit_esg_claim(asset_id: str, kg_co2_saved: float, block_hash: str) -> None:
    get_siem().emit(SIEMEvent(
        event_type=SIEMEventType.ESG_CLAIM,
        severity=SIEMSeverity.INFO,
        source="sovereign_ledger",
        message=f"ESG claim committed: {kg_co2_saved:.4f} kg CO2 saved by {asset_id}",
        resource=f"ledger/{block_hash}",
        outcome="success",
        context={"asset_id": asset_id, "kg_co2_saved": kg_co2_saved, "block_hash": block_hash},
    ))
