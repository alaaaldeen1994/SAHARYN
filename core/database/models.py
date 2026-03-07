import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .session import Base

class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    critical_thresholds = Column(JSON, nullable=True)

class SatelliteTelemetry(Base):
    """TimescaleDB Hypertable Ready"""
    __tablename__ = "satellite_telemetry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), primary_key=True, server_default=func.now(), index=True)
    site_id = Column(String, nullable=False, index=True)
    source_agency = Column(String, nullable=False) # NASA_MODIS_LIVE, COPERNICUS
    
    aod_550nm = Column(Float, nullable=False)
    dust_concentration = Column(Float, nullable=True)
    temp_2m_k = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)
    
    integrity_hash = Column(String, nullable=False) # SHA-256

class SensorTelemetry(Base):
    """TimescaleDB Hypertable Ready - Long Format"""
    __tablename__ = "sensor_telemetry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), primary_key=True, server_default=func.now(), index=True)
    site_id = Column(String, nullable=False, index=True)
    asset_id = Column(String, nullable=False, index=True)
    
    source_tag = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)
    
    quality_code = Column(String, default="192") # OPC-UA Good (192) or Bad (0)
    integrity_hash = Column(String, nullable=False) # SHA-256

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    asset_id = Column(String, nullable=False, index=True)
    site_id = Column(String, nullable=True)
    dsi_forecast = Column(Float, nullable=False)
    failure_prob = Column(Float, nullable=False)
    rec_action = Column(String, nullable=True)
    est_roi = Column(Float, nullable=True)

class AuditTrail(Base):
    __tablename__ = "audit_trail"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(String, nullable=True)
    action = Column(String, nullable=False)
    resource = Column(String, nullable=False)
    status = Column(String, nullable=False)
    details = Column(JSON, nullable=True)
