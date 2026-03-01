import numpy as np
from scipy.stats import ks_2samp
from typing import List, Dict
from core.common.base import get_logger

class DriftDetector:
    """
    Monitors data distributions for Data/Concept drift using Kolmogorov-Smirnov test.
    """
    
    def __init__(self, threshold: float = 0.05):
        self.logger = get_logger("DriftDetector")
        self.threshold = threshold
        self.reference_data = {} # Stores baseline distributions

    def set_reference(self, feature_name: str, values: List[float]):
        self.reference_data[feature_name] = values

    def check_drift(self, feature_name: str, current_values: List[float]) -> bool:
        if feature_name not in self.reference_data:
            return False
            
        statistic, p_value = ks_2samp(self.reference_data[feature_name], current_values)
        
        is_drifting = p_value < self.threshold
        if is_drifting:
            self.logger.warning(f"DRIFT DETECTED in {feature_name}: p-value={p_value:.4f}")
            # Trigger retraining event via Kafka
        
        return is_drifting

    def report_status(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "monitored_features": list(self.reference_data.keys()),
            "drift_events_last_24h": 0
        }
