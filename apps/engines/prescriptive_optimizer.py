import logging
import numpy as np
from typing import List, Dict, Any
from pydantic import BaseModel
from core.common.base import get_logger

logger = get_logger("PrescriptiveOptimizer")

class ActionOption(BaseModel):
    id: str
    label: str
    cost: float
    reduction_factor: float # Percentage reduction in failure probability
    downtime_hrs: float

class PrescriptiveOptimizationEngine:
    """
    Enterprise Prescriptive Optimizer.
    Converts failure probabilities and ROI simulations into actionable industrial directives.
    Goal: Minimize Total Cost (OpCost + Expected Failure Cost).
    """
    
    def __init__(self, energy_cost_per_mwh: float = 120, downtime_cost_per_hr: float = 8500):
        self.energy_cfg = energy_cost_per_mwh
        self.downtime_cfg = downtime_cost_per_hr
        
        # Standard Operating Procedure (SOP) Action Matrix
        self.action_matrix = [
            ActionOption(id="LOAD_SHED_10", label="Reduce Load by 10%", cost=500, reduction_factor=0.15, downtime_hrs=0),
            ActionOption(id="LOAD_SHED_30", label="Reduce Load by 30%", cost=2500, reduction_factor=0.45, downtime_hrs=0),
            ActionOption(id="ADVANCE_PM", label="Advance Planned Maintenance", cost=12000, reduction_factor=0.85, downtime_hrs=6),
            ActionOption(id="CLEAN_FILTERS", label="Emergency Filter Cleaning", cost=4500, reduction_factor=0.60, downtime_hrs=2)
        ]

    def optimize_decision(self, asset_id: str, failure_prob: float, asset_value: float) -> Dict[str, Any]:
        """
        Calculates the optimal action using Expected Value (EV) theory.
        Loss = P(Failure) * AssetValue 
        """
        logger.info(f"Optimizing prescriptive policy for {asset_id} (P_Fail: {failure_prob:.4f})")
        
        # Base Case: Do Nothing (Expected Loss)
        baseline_expected_loss = failure_prob * asset_value
        
        best_action = None
        best_roi = 0.0
        lowest_total_cost = baseline_expected_loss
        expected_savings = 0.0

        for action in self.action_matrix:
            # New failure prob after action
            new_prob = failure_prob * (1 - action.reduction_factor)
            
            # Action Cost = Fixed Cost + Operational Cost + Downtime Cost
            operational_impact = action.downtime_hrs * self.downtime_cfg
            total_action_cost = action.cost + operational_impact
            
            # New Expected Loss = (New Prob * Asset Value) + Action Cost
            new_expected_loss = (new_prob * asset_value) + total_action_cost
            
            # ROI = (Initial Loss - New EL) / Total Action Cost
            if new_expected_loss < lowest_total_cost:
                lowest_total_cost = new_expected_loss
                best_action = action
                expected_savings = baseline_expected_loss - new_expected_loss
                best_roi = (expected_savings / total_action_cost) if total_action_cost > 0 else 0

        if best_action and best_roi > 1.25: # ROI threshold for industrial approval
            return {
                "asset_id": asset_id,
                "recommended_action": best_action.label,
                "action_id": best_action.id,
                "expected_roi": round(best_roi, 2),
                "estimated_savings_usd": round(expected_savings, 2),
                "risk_reduction_pct": round(best_action.reduction_factor * 100, 1),
                "rational": f"Action {best_action.id} provides optimal cost mitigation. EV reduced by ${expected_savings:,.2f}."
            }
        
        return {
            "asset_id": asset_id,
            "recommended_action": "CONTINUE_NOMINAL_OPS",
            "action_id": "NOMINAL",
            "expected_roi": 0.0,
            "estimated_savings_usd": 0.0,
            "rational": "Expected loss from storm is below ROI threshold for intervention cost."
        }

if __name__ == "__main__":
    optimizer = PrescriptiveOptimizationEngine()
    # 35% failure probability on a $1.2M Compressor
    rec = optimizer.optimize_decision("TRAIN_01_COMP", 0.35, 1200000)
    print(rec)
