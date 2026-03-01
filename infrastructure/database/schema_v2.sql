-- SAHARYN AI v2.0 - PRODUCTION DATABASE SCHEMA
-- Target: PostgreSQL + TimescaleDB Extension
-- Description: Optimized for high-frequency industrial telemetry and spectral satellite data.

-- 1. BASE TABLES (Metadata)
CREATE TABLE IF NOT EXISTS industrial_sites (
    site_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    latitude DECIMAL(9,6) NOT NULL,
    longitude DECIMAL(9,6) NOT NULL,
    region VARCHAR(50),
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS assets (
    asset_id VARCHAR(50) PRIMARY KEY,
    site_id VARCHAR(50) REFERENCES industrial_sites(site_id),
    asset_type VARCHAR(50), -- e.g., 'Pump', 'Rotor', 'Solar_Array'
    model_variant VARCHAR(100),
    installation_date DATE,
    criticality_rank INTEGER CHECK (criticality_rank BETWEEN 1 AND 5),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. HYPERTABLES (Time-Series Data)
-- Satellite Telemetry (CAMS / MODIS)
CREATE TABLE IF NOT EXISTS satellite_telemetry (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    site_id VARCHAR(50) REFERENCES industrial_sites(site_id),
    aerosol_optical_depth FLOAT,
    dust_concentration_mg_m3 FLOAT,
    wind_speed_10m FLOAT,
    wind_direction_10m FLOAT,
    temperature_2m FLOAT,
    checksum_sha256 VARCHAR(64), -- Data Integrity Checksum
    verification_status VARCHAR(20) DEFAULT 'UNVERIFIED' -- [VERIFIED, ANOMALY, CORRUPT]
);

-- SCADA / IoT Telemetry
CREATE TABLE IF NOT EXISTS asset_telemetry (
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    asset_id VARCHAR(50) REFERENCES assets(asset_id),
    vibration_mm_s FLOAT,
    surface_temp_c FLOAT,
    power_consumption_kw FLOAT,
    flow_rate_m3_h FLOAT,
    load_factor FLOAT
);

-- 3. ANALYTICS & INFERENCE LOGS
CREATE TABLE IF NOT EXISTS inference_logs (
    inference_id UUID PRIMARY KEY,
    time TIMESTAMP WITH TIME ZONE NOT NULL,
    asset_id VARCHAR(50) REFERENCES assets(asset_id),
    failure_probability FLOAT,
    remaining_useful_life_hrs FLOAT,
    dominant_threat VARCHAR(50),
    prescriptive_action_id VARCHAR(50),
    model_version VARCHAR(20),
    inference_latency_ms INTEGER
);

-- 4. TIMESCALEDB HYPERTABLE INITIALIZATION (If extension exists)
-- SELECT create_hypertable('satellite_telemetry', 'time');
-- SELECT create_hypertable('asset_telemetry', 'time');

-- 5. INDEXING FOR PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_site_time ON satellite_telemetry (site_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_asset_time ON asset_telemetry (asset_id, time DESC);
