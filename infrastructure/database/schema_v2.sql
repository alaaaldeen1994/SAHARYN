-- =============================================================
-- SAHARYN AI v2.1 — PRODUCTION DATABASE SCHEMA
-- Target:   TimescaleDB (PostgreSQL 15 extension)
-- Purpose:  High-frequency industrial telemetry + satellite data
-- Updated:  2026-03-06
-- =============================================================

-- Enable TimescaleDB extension (must be first)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- =============================================================
-- 1. METADATA TABLES (Standard relational tables — no time-series)
-- =============================================================

CREATE TABLE IF NOT EXISTS industrial_sites (
    site_id         VARCHAR(50) PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    latitude        DECIMAL(9,6) NOT NULL,
    longitude       DECIMAL(9,6) NOT NULL,
    region          VARCHAR(50),
    country         VARCHAR(50) DEFAULT 'SA',
    timezone        VARCHAR(50) DEFAULT 'Asia/Riyadh',
    elevation_m     FLOAT,
    site_type       VARCHAR(50),    -- e.g., 'oil_refinery', 'solar_farm', 'pipeline'
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS assets (
    asset_id            VARCHAR(50) PRIMARY KEY,
    site_id             VARCHAR(50) NOT NULL REFERENCES industrial_sites(site_id) ON DELETE CASCADE,
    asset_type          VARCHAR(50) NOT NULL,   -- 'Pump', 'Compressor', 'Heat_Exchanger', 'Filter', 'Cooling_Unit'
    manufacturer        VARCHAR(100),
    model_variant       VARCHAR(100),
    installation_date   DATE,
    design_life_years   INTEGER,
    criticality_rank    INTEGER CHECK (criticality_rank BETWEEN 1 AND 5),
    parent_asset_id     VARCHAR(50) REFERENCES assets(asset_id),   -- for sub-components
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS maintenance_schedules (
    schedule_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id            VARCHAR(50) NOT NULL REFERENCES assets(asset_id),
    maintenance_type    VARCHAR(50),    -- 'filter_replacement', 'bearing_inspection', 'oil_change'
    scheduled_date      DATE NOT NULL,
    completed_date      DATE,
    status              VARCHAR(20) DEFAULT 'SCHEDULED',   -- SCHEDULED, DONE, OVERDUE
    technician_id       VARCHAR(50),
    cost_usd            FLOAT,
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================
-- 2. TIME-SERIES TABLES (Will be converted to TimescaleDB hypertables)
-- =============================================================

-- Satellite + Atmospheric data (from Copernicus CAMS, NASA MODIS, Sentinel-2)
CREATE TABLE IF NOT EXISTS satellite_telemetry (
    time                        TIMESTAMPTZ     NOT NULL,
    site_id                     VARCHAR(50)     NOT NULL REFERENCES industrial_sites(site_id),
    -- Aerosol / Dust
    aerosol_optical_depth       FLOAT,          -- AOD at 550nm (dimensionless, 0-5)
    dust_concentration_ug_m3    FLOAT,          -- μg/m³
    pm10_concentration_ug_m3    FLOAT,          -- PM10 μg/m³
    -- Wind
    wind_speed_10m              FLOAT,          -- m/s at 10m height
    wind_direction_10m          FLOAT,          -- degrees (0-360)
    wind_speed_100m             FLOAT,          -- m/s at 100m (for turbines)
    -- Temperature & Humidity
    temperature_2m_c            FLOAT,          -- °C at 2m
    relative_humidity_pct       FLOAT,          -- %
    surface_pressure_hpa        FLOAT,          -- hPa
    -- Derived / Computed
    dust_severity_index         FLOAT,          -- DSI: 0.0-1.0 (SAHARYN formula)
    storm_probability_72h       FLOAT,          -- 0.0-1.0
    -- Data Lineage
    data_source                 VARCHAR(50),    -- 'COPERNICUS_CAMS', 'NASA_MODIS', 'SENTINEL2'
    data_version                VARCHAR(20),
    checksum_sha256             VARCHAR(64),
    verification_status         VARCHAR(20) DEFAULT 'UNVERIFIED'   -- VERIFIED, ANOMALY, CORRUPT
);

-- SCADA / OPC-UA / PI Server telemetry (1-minute frequency)
CREATE TABLE IF NOT EXISTS asset_telemetry (
    time                        TIMESTAMPTZ     NOT NULL,
    asset_id                    VARCHAR(50)     NOT NULL REFERENCES assets(asset_id),
    -- Mechanical
    vibration_mm_s              FLOAT,          -- mm/s RMS
    bearing_temp_c              FLOAT,          -- °C
    surface_temp_c              FLOAT,          -- °C
    -- Process
    flow_rate_m3_h              FLOAT,          -- m³/h
    inlet_pressure_bar          FLOAT,          -- bar
    outlet_pressure_bar         FLOAT,          -- bar
    differential_pressure_bar   FLOAT,          -- bar
    -- Electrical
    power_consumption_kw        FLOAT,          -- kW
    current_amps                FLOAT,          -- A
    voltage_v                   FLOAT,          -- V
    load_factor                 FLOAT,          -- 0.0-1.0
    -- Efficiency
    efficiency_pct              FLOAT,          -- %
    -- Data Quality
    data_source                 VARCHAR(50),    -- 'OPC_UA', 'PI_SERVER', 'MANUAL'
    quality_code                INTEGER DEFAULT 192   -- OPC-UA quality code (192 = Good)
);

-- AI Model inference results
CREATE TABLE IF NOT EXISTS inference_logs (
    inference_id                UUID            NOT NULL DEFAULT gen_random_uuid(),
    time                        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    asset_id                    VARCHAR(50)     NOT NULL REFERENCES assets(asset_id),
    -- Risk outputs
    failure_probability         FLOAT,          -- 0.0-1.0
    remaining_useful_life_hrs   FLOAT,
    efficiency_drop_pct         FLOAT,
    dust_severity_index         FLOAT,
    -- Root cause
    dominant_threat             VARCHAR(50),    -- 'DUST_INGESTION', 'THERMAL_STRESS', 'VIBRATION'
    causal_root_node            VARCHAR(50),
    -- Prescription
    prescriptive_action_key     VARCHAR(100),
    roi_estimate_usd            FLOAT,
    avoided_downtime_hrs        FLOAT,
    -- MLOps
    model_version               VARCHAR(30),
    model_name                  VARCHAR(50),
    inference_latency_ms        INTEGER,
    drift_detected              BOOLEAN DEFAULT FALSE,
    -- Audit
    request_trace_id            UUID,
    caller_id                   VARCHAR(100)
);

-- Prescriptive action history (what was recommended and what happened)
CREATE TABLE IF NOT EXISTS action_outcomes (
    outcome_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    inference_id        UUID NOT NULL,
    asset_id            VARCHAR(50) NOT NULL REFERENCES assets(asset_id),
    time_recommended    TIMESTAMPTZ NOT NULL,
    time_executed       TIMESTAMPTZ,
    action_key          VARCHAR(100),
    status              VARCHAR(20) DEFAULT 'PENDING',  -- PENDING, EXECUTED, REJECTED, EXPIRED
    actual_roi_usd      FLOAT,
    operator_id         VARCHAR(50),
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ESG / Carbon ledger (immutable append-only blocks)
CREATE TABLE IF NOT EXISTS esg_ledger (
    time                TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    block_index         BIGSERIAL,
    inference_id        UUID            NOT NULL,
    asset_id            VARCHAR(50)     NOT NULL,
    action_type         VARCHAR(100),
    co2_kg_saved        FLOAT,
    water_liters_saved  FLOAT,
    energy_kwh_saved    FLOAT,
    verification_hash   VARCHAR(128)    NOT NULL,
    previous_hash       VARCHAR(128)
);

-- =============================================================
-- 3. CONVERT TIME-SERIES TABLES TO TIMESCALE HYPERTABLES
--    Partitioned by time — dramatically improves query performance
--    on large datasets (10M+ rows/day)
-- =============================================================

SELECT create_hypertable(
    'satellite_telemetry', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

SELECT create_hypertable(
    'asset_telemetry', 'time',
    chunk_time_interval => INTERVAL '1 hour',   -- 1-min SCADA data = dense, use 1h chunks
    if_not_exists => TRUE
);

SELECT create_hypertable(
    'inference_logs', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

SELECT create_hypertable(
    'esg_ledger', 'time',
    chunk_time_interval => INTERVAL '30 days',
    if_not_exists => TRUE
);

-- =============================================================
-- 4. COMPRESSION (Saves 90%+ storage on old time-series data)
-- =============================================================

ALTER TABLE satellite_telemetry SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC',
    timescaledb.compress_segmentby = 'site_id'
);

ALTER TABLE asset_telemetry SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC',
    timescaledb.compress_segmentby = 'asset_id'
);

-- Auto-compress chunks older than 7 days
SELECT add_compression_policy('satellite_telemetry', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_compression_policy('asset_telemetry', INTERVAL '7 days', if_not_exists => TRUE);

-- =============================================================
-- 5. RETENTION POLICY (Auto-delete old raw data to manage storage)
-- =============================================================

-- Keep raw SCADA data for 90 days (compressed, then deleted)
SELECT add_retention_policy('asset_telemetry', INTERVAL '90 days', if_not_exists => TRUE);
-- Keep satellite data for 365 days
SELECT add_retention_policy('satellite_telemetry', INTERVAL '365 days', if_not_exists => TRUE);

-- =============================================================
-- 6. INDEXES (Performance optimization for common queries)
-- =============================================================

-- Satellite queries: site + time range
CREATE INDEX IF NOT EXISTS idx_sat_site_time
    ON satellite_telemetry (site_id, time DESC);

-- SCADA queries: asset + time range
CREATE INDEX IF NOT EXISTS idx_asset_time
    ON asset_telemetry (asset_id, time DESC);

-- Inference queries: asset + failure probability
CREATE INDEX IF NOT EXISTS idx_inference_asset_time
    ON inference_logs (asset_id, time DESC);

CREATE INDEX IF NOT EXISTS idx_inference_failure_prob
    ON inference_logs (failure_probability DESC, time DESC)
    WHERE failure_probability > 0.5;   -- Partial index — only high-risk events

-- ESG ledger: audit queries
CREATE INDEX IF NOT EXISTS idx_esg_asset_time
    ON esg_ledger (asset_id, time DESC);

-- =============================================================
-- 7. SEED DATA (Minimum required for system startup)
-- =============================================================

INSERT INTO industrial_sites (site_id, name, latitude, longitude, region, site_type)
VALUES
    ('SA_EAST_RU_01', 'Eastern Province Refinery Unit 01', 26.4367, 50.1033, 'Eastern Province', 'oil_refinery'),
    ('SA_NEOM_01',    'NEOM Solar & Wind Complex',         28.0000, 35.0000, 'NEOM',            'solar_farm'),
    ('SA_DHAHRAN_01', 'Dhahran Industrial Complex',        26.2361, 50.0393, 'Eastern Province', 'industrial_complex')
ON CONFLICT (site_id) DO NOTHING;

INSERT INTO assets (asset_id, site_id, asset_type, criticality_rank)
VALUES
    ('PUMP_RU_42',      'SA_EAST_RU_01', 'Pump',          5),
    ('COMP_RU_01',      'SA_EAST_RU_01', 'Compressor',    5),
    ('FILTER_RU_07',    'SA_EAST_RU_01', 'Filter',        4),
    ('HEX_RU_03',       'SA_EAST_RU_01', 'Heat_Exchanger',4),
    ('ROTOR_NEOM_01',   'SA_NEOM_01',    'Rotor',         5)
ON CONFLICT (asset_id) DO NOTHING;
