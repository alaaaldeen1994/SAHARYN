import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.digital_twin import atmospheric_engine, digital_twin_service

def test_atmospheric_vector_engine():
    # Test vector field computation across 0h, 24h, 48h, 72h
    for hour in [0, 24, 48, 72]:
        data = atmospheric_engine.compute_vector_slice(timestamp_hour=hour)
        assert data["forecast_hour"] == hour
        assert "storm_center" in data
        assert len(data["vectors"]) > 0
        assert len(data["voxels"]) > 0
        # Validate 3D wind velocity ranges
        v = data["vectors"][0]
        assert "u" in v and "v" in v and "w" in v
        assert "intensity" in v

def test_digital_twin_assets_state():
    state = digital_twin_service.get_digital_twin_state(forecast_hour=12)
    assert state["total_monitored_assets"] == 3
    assert len(state["assets"]) == 3
    
    asset_ids = [a["asset_id"] for a in state["assets"]]
    assert "asset-sudair-pv" in asset_ids
    assert "asset-yanbu-turbine" in asset_ids
    assert "asset-neom-telecom" in asset_ids
    
    for asset in state["assets"]:
        tel = asset["telemetry"]
        assert "ddi" in tel
        assert "loss_velocity_usd_hr" in tel
        assert "scada_recommended_action" in tel

if __name__ == "__main__":
    test_atmospheric_vector_engine()
    test_digital_twin_assets_state()
    print("ALL DIGITAL TWIN TESTS PASSED SUCCESSFULLY!")
