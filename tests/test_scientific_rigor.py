import pytest
import numpy as np
from apps.ai_core.models import DustSeverityModel, MechanicalReliabilityModel
from core.common.geology import GeotechnicalDustProfiler

def test_dust_model_physics_limits():
    """Verify the environmental model obeys physical constraints."""
    model = DustSeverityModel()
    # High AOD, High Wind, Low Humidity should result in high DSI
    res = model.predict(aod=1.5, wind_speed=25.0, humidity=5.0)
    assert 0.0 <= res.value <= 1.0
    assert res.value > 0.5
    # Variance should increase with wind speed
    low_wind = model.predict(aod=0.5, wind_speed=2.0, humidity=20.0)
    high_wind = model.predict(aod=0.5, wind_speed=40.0, humidity=20.0)
    assert (high_wind.confidence_interval[1] - high_wind.confidence_interval[0]) > \
           (low_wind.confidence_interval[1] - low_wind.confidence_interval[0])

def test_geology_abrasivity():
    """Verify mineralogical wear scaling."""
    profiler = GeotechnicalDustProfiler(region="Rub_Al_Khali")
    multiplier = profiler.get_abrasivity_multiplier()
    assert multiplier > 1.0 # High quartz content should scale wear

    deposition = profiler.estimate_deposition_rate(wind_speed=10, dsi=0.8)
    assert deposition > 0

def test_mechanical_thermokinetics():
    """Verify Arrhenius-style thermal stress logic."""
    model = MechanicalReliabilityModel("Compressor")
    normal_op = model.predict({"temp": 30.0, "efficiency": 0.9}, dsi=0.5)
    extreme_op = model.predict({"temp": 55.0, "efficiency": 0.9}, dsi=0.5)
    assert extreme_op["stress_metrics"]["thermal_stress"] > normal_op["stress_metrics"]["thermal_stress"]
    assert extreme_op["failure_probability"] > normal_op["failure_probability"]
