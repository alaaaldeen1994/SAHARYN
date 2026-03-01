import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from .session import Base

class Asset(Base):
    __tablename__ = "assets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    critical_thresholds = Column(JSON, nullable=True)

class Prediction(Base):
    __tablename__ = "predictions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    asset_id = Column(String, nullable=False) # Simplified for current integration
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
