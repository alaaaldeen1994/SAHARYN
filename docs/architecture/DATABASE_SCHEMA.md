# Database Schema Design

## 1. TimescaleDB (Time-Series Data)

### 1.1 Environmental Metrics (`environmental_metrics`)
| Column | Type | Description |
|--------|------|-------------|
| time | TIMESTAMPTZ | Event timestamp |
| asset_id | UUID | FK to assets |
| aod | FLOAT | Aerosol Optical Depth |
| dust_conc | FLOAT | Dust concentration |
| temp | FLOAT | Ambient temperature |
| humidity | FLOAT | Relative humidity |
| wind_speed | FLOAT | Local wind speed |
| wind_dir | FLOAT | Local wind direction |

### 1.2 Asset Telemetry (`asset_telemetry`)
| Column | Type | Description |
|--------|------|-------------|
| time | TIMESTAMPTZ | Event timestamp |
| asset_id | UUID | FK to assets |
| pressure | FLOAT | Inlet/Outlet pressure |
| flow | FLOAT | Fluid flow rate |
| vibration | FLOAT | Vibration magnitude |
| power | FLOAT | Energy consumption |
| efficiency | FLOAT | Calculated efficiency |

## 2. PostgreSQL (Metadata & Results)

### 2.1 Assets (`assets`)
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | PK |
| name | VARCHAR | Asset name |
| type | VARCHAR | Pump, Compressor, etc. |
| parent_id | UUID | For causal graph hierarchy |
| critical_threshold | JSONB | Operational limits |

### 2.2 Maintenance Logs (`maintenance_logs`)
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | PK |
| asset_id | UUID | FK to assets |
| work_order_id | VARCHAR | External ID (SAP/Maximo) |
| type | VARCHAR | Repair, PM, Inspection |
| status | VARCHAR | Completed, Pending |
| completed_at | TIMESTAMPTZ | Completion time |

### 2.3 Predictions & Recommendations (`predictions`)
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | PK |
| timestamp | TIMESTAMPTZ | Creation time |
| asset_id | UUID | FK to assets |
| dsi_forecast | FLOAT | Dust Severity Index |
| failure_prob | FLOAT | Predicted failure prob |
| rec_action | TEXT | Prescriptive recommendation |
| est_roi | FLOAT | Estimated savings |

### 2.4 Audit & Compliance (`audit_trail`)
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | PK |
| timestamp | TIMESTAMPTZ | Log time |
| user_id | UUID | Performing user |
| action | VARCHAR | Action name |
| resource | VARCHAR | Affected resource |
| status | VARCHAR | Success/Failure |
| details | JSONB | Full payload for traceability |
