"""
SAHARYN 3D Volumetric Digital Twin Service
==========================================
Coordinates 3D WGS84 asset instances (Solar PV, Gas Turbines, 5G Towers),
computes dynamic surface degradation (optical loss, kinetic blade erosion),
and handles closed-loop SCADA robotic actuation triggers.
"""

from typing import Dict, Any
import time

class DigitalTwinService:
    def __init__(self):
        # High-consequence 3D infrastructure sites across Saudi Arabia
        self.assets = [
            {
                "id": "asset-sudair-pv",
                "name": "Sudair Solar PV Complex (1.5 GW)",
                "category": "solar_pv",
                "lat": 25.688,
                "lon": 45.625,
                "altitude_m": 612.0,
                "specs": {
                    "total_capacity_mw": 1500,
                    "module_technology": "N-Type TOPCon Bifacial",
                    "tracker_type": "Single-Axis Horizontal Tracking",
                    "total_modules": 3200000,
                    "cleaning_robot_fleet": "Autonomous Dry-Sweeping (580 units)"
                },
                "baseline_cleanliness": 0.985,
                "critical_ddi_threshold": 0.082
            },
            {
                "id": "asset-yanbu-turbine",
                "name": "Yanbu Industrial Gas Turbine Unit #4",
                "category": "gas_turbine",
                "lat": 24.089,
                "lon": 38.063,
                "altitude_m": 18.0,
                "specs": {
                    "turbine_model": "Heavy-Duty Frame 7F.05",
                    "rated_power_mw": 240,
                    "air_intake_filtration": "Three-Stage HEPA H13 Pulse-Clean",
                    "rated_airflow_kg_s": 520
                },
                "baseline_cleanliness": 1.0,
                "critical_ddi_threshold": 0.12
            },
            {
                "id": "asset-neom-telecom",
                "name": "NEOM Mountain 5G Backhaul Relay Node #12",
                "category": "telecom_tower",
                "lat": 28.125,
                "lon": 35.312,
                "altitude_m": 1280.0,
                "specs": {
                    "frequency_band": "28 GHz Millimeter-Wave + E-Band 80 GHz",
                    "polarization": "Dual Circular (RHCP/LHCP)",
                    "radome_coating": "Hydrophobic Anti-Dust Nanofilm"
                },
                "baseline_cleanliness": 1.0,
                "critical_ddi_threshold": 0.15
            }
        ]

    def compute_asset_degradation(self, asset: Dict[str, Any], storm_intensity: float) -> Dict[str, Any]:
        """
        Computes dynamic physical degradation, financial loss velocity,
        and SCADA actuation status given current local atmospheric particulate flux.
        """
        category = asset["category"]
        
        # Dust Deposition Index (DDI) increases with storm intensity
        ddi = round(min(0.35, storm_intensity * 0.22), 4)
        optical_transmittance_loss_pct = round(ddi * 100.0 * 1.15, 2)
        
        if category == "solar_pv":
            power_loss_mw = round(asset["specs"]["total_capacity_mw"] * (optical_transmittance_loss_pct / 100.0), 1)
            revenue_loss_usd_hr = round(power_loss_mw * 42.50, 1) # $42.5/MWh PPA tariff
            status = "CRITICAL_SOILING" if ddi > asset["critical_ddi_threshold"] else "NOMINAL"
            action = "TRIGGER_AUTONOMOUS_ROBOTIC_SWEEP" if ddi > asset["critical_ddi_threshold"] else "STANDBY"
            metric_label = "Optical Transmittance Loss"
            metric_val = f"-{optical_transmittance_loss_pct}%"
        elif category == "gas_turbine":
            filter_dp_pa = round(250 + ddi * 1800.0, 1) # Filter pressure drop
            heat_rate_penalty_pct = round(ddi * 14.0, 2)
            revenue_loss_usd_hr = round(240 * (heat_rate_penalty_pct / 100.0) * 65.0, 1)
            status = "FILTER_CLOGGING" if ddi > asset["critical_ddi_threshold"] else "NOMINAL"
            action = "PULSE_JET_BACKFLUSH_STAGE2" if ddi > asset["critical_ddi_threshold"] else "STANDBY"
            metric_label = "Compressor Intake ΔP"
            metric_val = f"{filter_dp_pa} Pa"
        else: # telecom_tower
            attenuation_db_km = round(ddi * 24.5, 2)
            link_margin_db = round(max(0.0, 18.5 - attenuation_db_km), 1)
            revenue_loss_usd_hr = 450.0 if link_margin_db < 3.0 else 0.0
            status = "ATTENUATION_FADE" if link_margin_db < 4.0 else "NOMINAL"
            action = "ADAPTIVE_MODULATION_QPSK_FALLBACK" if link_margin_db < 4.0 else "STANDBY"
            metric_label = "Atmospheric RF Attenuation"
            metric_val = f"+{attenuation_db_km} dB/km"

        return {
            "asset_id": asset["id"],
            "name": asset["name"],
            "category": category,
            "coordinates": {"lat": asset["lat"], "lon": asset["lon"], "alt_m": asset["altitude_m"]},
            "specs": asset["specs"],
            "telemetry": {
                "ddi": ddi,
                "metric_label": metric_label,
                "metric_value": metric_val,
                "loss_velocity_usd_hr": revenue_loss_usd_hr,
                "health_status": status,
                "scada_recommended_action": action,
                "last_calibrated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
        }

    def get_digital_twin_state(self, forecast_hour: int = 0) -> Dict[str, Any]:
        """
        Returns the synchronized 3D digital twin state for all monitored assets
        at the specified forecast horizon.
        """
        # Calculate localized storm intensity for each asset based on forecast hour
        t_phase = forecast_hour / 72.0
        storm_center_lat = 29.0 - (t_phase * 7.5)
        storm_center_lon = 42.0 + (t_phase * 6.5)

        results = []
        for asset in self.assets:
            dist = ((asset["lat"] - storm_center_lat)**2 + (asset["lon"] - storm_center_lon)**2)**0.5
            intensity = max(0.05, 1.0 - (dist / 6.0)) if dist < 6.0 else 0.05
            results.append(self.compute_asset_degradation(asset, intensity))

        return {
            "forecast_hour": forecast_hour,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_monitored_assets": len(results),
            "total_avoidable_loss_usd_hr": round(sum(a["telemetry"]["loss_velocity_usd_hr"] for a in results), 1),
            "assets": results
        }

digital_twin_service = DigitalTwinService()
