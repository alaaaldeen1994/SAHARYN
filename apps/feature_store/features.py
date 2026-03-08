"""
SAHARYN AI — Feast Feature Store Setup
=======================================
Defines all ML features used across models.
Features are grouped into Feature Views that pull from:
  - TimescaleDB (operational data source)
  - Satellite telemetry
  - Asset telemetry
  - Maintenance logs

Production usage:
    from apps.feature_store.store import SAHARYNFeatureStore
    store = SAHARYNFeatureStore()
    features = store.get_online_features("PUMP_RU_42")
"""

from datetime import timedelta
from feast import (
    Entity,
    FeatureService,
    FeatureView,
    Field,
)
from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import (
    PostgreSQLSource,
)
from feast.types import Float32, String


# ─────────────────────────────────────────────────────────────
# ENTITIES — The primary keys that identify data records
# ─────────────────────────────────────────────────────────────

site_entity = Entity(
    name="site_id",
    description="Unique identifier for an industrial site (e.g., SA_EAST_RU_01)",
    value_type=String,
    join_keys=["site_id"],
)

asset_entity = Entity(
    name="asset_id",
    description="Unique identifier for an industrial asset (e.g., PUMP_RU_42)",
    value_type=String,
    join_keys=["asset_id"],
)


# ─────────────────────────────────────────────────────────────
# DATA SOURCES — Pull from TimescaleDB (PostgreSQL)
# ─────────────────────────────────────────────────────────────

satellite_source = PostgreSQLSource(
    name="satellite_telemetry_source",
    query="""
        SELECT
            site_id,
            time AS event_timestamp,
            aerosol_optical_depth,
            dust_concentration_ug_m3,
            pm10_concentration_ug_m3,
            wind_speed_10m,
            wind_direction_10m,
            temperature_2m_c,
            relative_humidity_pct,
            surface_pressure_hpa,
            dust_severity_index,
            storm_probability_72h
        FROM satellite_telemetry
        WHERE verification_status = 'VERIFIED'
    """,
    timestamp_field="event_timestamp",
)

asset_telemetry_source = PostgreSQLSource(
    name="asset_telemetry_source",
    query="""
        SELECT
            asset_id,
            time AS event_timestamp,
            vibration_mm_s,
            bearing_temp_c,
            surface_temp_c,
            flow_rate_m3_h,
            inlet_pressure_bar,
            outlet_pressure_bar,
            differential_pressure_bar,
            power_consumption_kw,
            load_factor,
            efficiency_pct
        FROM asset_telemetry
        WHERE quality_code >= 192
    """,
    timestamp_field="event_timestamp",
)

inference_features_source = PostgreSQLSource(
    name="inference_logs_source",
    query="""
        SELECT
            asset_id,
            time AS event_timestamp,
            failure_probability,
            remaining_useful_life_hrs,
            efficiency_drop_pct,
            dust_severity_index,
            dominant_threat
        FROM inference_logs
        WHERE drift_detected = FALSE
    """,
    timestamp_field="event_timestamp",
)


# ─────────────────────────────────────────────────────────────
# FEATURE VIEWS — Group of related features served together
# ─────────────────────────────────────────────────────────────

satellite_features = FeatureView(
    name="satellite_environmental_features",
    entities=[site_entity],
    ttl=timedelta(hours=24),            # Features expire after 24h (satellite is daily)
    schema=[
        Field(name="aerosol_optical_depth",     dtype=Float32),
        Field(name="dust_concentration_ug_m3",  dtype=Float32),
        Field(name="pm10_concentration_ug_m3",  dtype=Float32),
        Field(name="wind_speed_10m",            dtype=Float32),
        Field(name="wind_direction_10m",        dtype=Float32),
        Field(name="temperature_2m_c",          dtype=Float32),
        Field(name="relative_humidity_pct",     dtype=Float32),
        Field(name="surface_pressure_hpa",      dtype=Float32),
        Field(name="dust_severity_index",       dtype=Float32),
        Field(name="storm_probability_72h",     dtype=Float32),
    ],
    online=True,
    source=satellite_source,
    tags={
        "data_source": "copernicus_cams",
        "update_frequency": "daily",
        "owner": "data_engineering",
    },
)

asset_operational_features = FeatureView(
    name="asset_operational_features",
    entities=[asset_entity],
    ttl=timedelta(hours=1),             # SCADA data expires after 1h (1-min frequency)
    schema=[
        Field(name="vibration_mm_s",            dtype=Float32),
        Field(name="bearing_temp_c",            dtype=Float32),
        Field(name="surface_temp_c",            dtype=Float32),
        Field(name="flow_rate_m3_h",            dtype=Float32),
        Field(name="inlet_pressure_bar",        dtype=Float32),
        Field(name="outlet_pressure_bar",       dtype=Float32),
        Field(name="differential_pressure_bar", dtype=Float32),
        Field(name="power_consumption_kw",      dtype=Float32),
        Field(name="load_factor",               dtype=Float32),
        Field(name="efficiency_pct",            dtype=Float32),
    ],
    online=True,
    source=asset_telemetry_source,
    tags={
        "data_source": "scada_opc_ua",
        "update_frequency": "1_minute",
        "owner": "operations",
    },
)

asset_risk_features = FeatureView(
    name="asset_risk_features",
    entities=[asset_entity],
    ttl=timedelta(hours=6),
    schema=[
        Field(name="failure_probability",       dtype=Float32),
        Field(name="remaining_useful_life_hrs", dtype=Float32),
        Field(name="efficiency_drop_pct",       dtype=Float32),
        Field(name="dust_severity_index",       dtype=Float32),
    ],
    online=True,
    source=inference_features_source,
    tags={
        "data_source": "inference_engine",
        "update_frequency": "5_minutes",
        "owner": "ai_core",
    },
)


# ─────────────────────────────────────────────────────────────
# FEATURE SERVICES — Bundles consumed by each model
# ─────────────────────────────────────────────────────────────

# Used by Layer 1: Environmental Impact Model
dust_severity_service = FeatureService(
    name="dust_severity_model_features",
    features=[
        satellite_features[["aerosol_optical_depth", "wind_speed_10m",
                            "temperature_2m_c", "relative_humidity_pct",
                            "pm10_concentration_ug_m3"]],
    ],
    tags={"model": "DustSeverityModel", "layer": "1"},
)

# Used by Layer 2: Asset Performance Predictor
asset_performance_service = FeatureService(
    name="asset_performance_model_features",
    features=[
        satellite_features[["dust_severity_index", "temperature_2m_c"]],
        asset_operational_features[[
            "vibration_mm_s", "surface_temp_c", "efficiency_pct",
            "differential_pressure_bar", "load_factor"
        ]],
    ],
    tags={"model": "AssetPerformanceModel", "layer": "2"},
)

# Used by Layer 3: Causal Graph + Prescriptive Optimizer
full_inference_service = FeatureService(
    name="full_inference_features",
    features=[
        satellite_features,
        asset_operational_features,
        asset_risk_features,
    ],
    tags={"model": "FullInferencePipeline", "layer": "3"},
)
