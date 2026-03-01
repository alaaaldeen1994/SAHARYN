import numpy as np
from typing import Dict, Any, Optional
from core.common.base import get_logger

class GeotechnicalDustProfiler:
    """
    Expert system for Geological Dust Analysis.
    Differentiates between Sand (abrasive/fast settling) and Silt/Clay (airborne/lung-penetrating/reactive).
    """
    def __init__(self, region: str = "Middle_East_Rub_Al_Khali"):
        self.logger = get_logger("GeologicalContext")
        self.region = region
        # Particle size distribution by region (micrometers)
        self.GEOLOGY_PROFILES = {
            "Rub_Al_Khali": {"quartz_content": 0.85, "median_diameter": 120, "abrasivity_index": 0.9},
            "Sahara_East": {"quartz_content": 0.70, "median_diameter": 45, "abrasivity_index": 0.6},
            "Australian_Outback": {"iron_oxide_content": 0.15, "median_diameter": 30, "abrasivity_index": 0.5}
        }

    def get_abrasivity_multiplier(self) -> float:
        """
        Calculates a multiplier for mechanical wear based on mineralogy.
        Higher quartz content = Higher Mohs hardness = Greater wear on impellers.
        """
        profile = self.GEOLOGY_PROFILES.get(self.region, self.GEOLOGY_PROFILES["Rub_Al_Khali"])
        # Mohs-Hardness weighted index
        return profile["quartz_content"] * profile["abrasivity_index"] * 1.5

    def estimate_deposition_rate(self, wind_speed: float, dsi: float) -> float:
        """
        Physics-based deposition modeling (kg/m^2/hr)
        v_d = Settling Velocity * Concentration
        """
        profile = self.GEOLOGY_PROFILES.get(self.region, self.GEOLOGY_PROFILES["Rub_Al_Khali"])
        # Stokes' Law approximation for particle settling
        g = 9.81
        rho_p = 2650 # Density of quartz in kg/m^3
        rho_a = 1.225 # Air density
        mu = 1.8e-5 # Air viscosity
        d = profile["median_diameter"] * 1e-6 # Convert to meters
        
        v_settling = (g * d**2 * (rho_p - rho_a)) / (18 * mu)
        
        # Adjust for turbulence: High wind keeps small particles aloft
        turbulent_bypass = np.exp(-0.1 * wind_speed)
        
        deposition_rate = v_settling * dsi * turbulent_bypass * 1000 # Scaling for mg/m^2
        return float(deposition_rate)
