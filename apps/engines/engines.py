import numpy as np
from typing import List, Dict, Any
from core.common.base import get_logger

class PrescriptiveOptimizer:
    """
    Generates cost-aware recommendations to minimize Operational Expenditure (OPEX)
    and avoid downtime losses.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = get_logger("PrescriptiveOptimizer")
        self.maintenance_cost_base = config.get("maint_cost", 5000)
        self.emergency_repair_cost = config.get("emergency_cost", 25000)
        self.downtime_cost_per_hour = config.get("downtime_cost", 10000)

    def optimize_schedule(self, failure_probs: Dict[str, float], time_horizon_h: int = 72) -> List[Dict[str, Any]]:
        """
        Decision logic: If Cost(Preventive) < P(Failure) * Cost(Emergency), recommend maintenance.
        """
        recommendations = []
        for asset_id, prob in failure_probs.items():
            expected_loss = prob * (self.emergency_repair_cost + (self.downtime_cost_per_hour * 8)) # Assume 8h fix
            
            if prob > 0.5:
                recommendations.append({
                    "asset_id": asset_id,
                    "action": "IMMEDIATE_LOAD_REDUCTION",
                    "reason": f"High failure probability ({prob:.2f})",
                    "priority": "CRITICAL",
                    "est_savings": expected_loss * 0.8 # Assume 80% risk mitigation
                })
            elif expected_loss > self.maintenance_cost_base:
                recommendations.append({
                    "asset_id": asset_id,
                    "action": "ADVANCE_PM",
                    "reason": f"Economic optimization: Expected failure loss exceeds PM cost.",
                    "priority": "HIGH",
                    "est_savings": expected_loss - self.maintenance_cost_base
                })
        
        return recommendations

class FinancialSimulator:
    """
    Runs Monte Carlo simulations to validate the ROI of the resilience platform.
    """
    
    def run_simulation(self, n_trials: int = 1000, storm_freq: float = 0.05):
        """
        Simulates a year of operations with vs without the platform.
        """
        results_without = []
        results_with = []
        
        for _ in range(n_trials):
            # Baseline (No AI)
            storms = np.random.binomial(365, storm_freq)
            failures = np.random.binomial(storms, 0.4) # 40% failure rate in storms
            cost_baseline = failures * 30000 
            
            # With Platform (80% mitigation)
            mitigated_failures = np.random.binomial(storms, 0.08)
            cost_with = (mitigated_failures * 30000) + (storms * 5000) # Savings + intervention cost
            
            results_without.append(cost_baseline)
            results_with.append(cost_with)
            
        return {
            "avg_saving": np.mean(results_without) - np.mean(results_with),
            "roi_ratio": (np.mean(results_without) - np.mean(results_with)) / 100000, # Assume 100k SaaS cost
            "confidence_95": np.percentile(results_with, 95)
        }
