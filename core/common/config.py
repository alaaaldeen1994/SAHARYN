from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from typing import Optional

class Settings(BaseSettings):
    # Professional Configuration Management
    app_name: str = "AI Desert Infrastructure Resilience Platform"
    environment: str = Field(default="production", env="ENV")
    
    # API Security
    api_secret: SecretStr = Field(..., env="API_SECRET")
    
    # Infrastructure
    postgres_url: str = Field(..., env="DATABASE_URL")
    kafka_brokers: str = Field(..., env="KAFKA_BROKERS")
    
    # Scientific Connectors
    ee_project_id: str = Field(..., env="GEE_PROJECT_ID")
    cds_api_key: SecretStr = Field(..., env="CDS_API_KEY")
    
    # Operational Thresholds
    dsi_critical_threshold: float = 0.75
    roi_simulation_trials: int = 10000
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

# Singleton instance for high-performance dependency injection
settings = Settings(_env_file=".env")
