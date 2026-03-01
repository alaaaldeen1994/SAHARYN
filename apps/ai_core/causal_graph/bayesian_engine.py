import logging
import networkx as nx
import numpy as np
from typing import Dict, List, Any, Optional
from core.common.base import get_logger

logger = get_logger("CausalBayesianEngine")

class CausalBayesianEngine:
    """
    Enterprise Layer 3 AI Engine.
    Propagates failure probabilities across directed infrastructure graphs.
    Uses Bayesian Inference to quantify joint risk and cascading failure likelihood.
    """
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.asset_risks = {} # Local failure probs

    def initialize_site_mesh(self, site_data: Dict[str, Any]):
        """
        Dynamically construct a site-specific dependency mesh from digital twin metadata.
        """
        site_id = site_data['site_id']
        logger.info(f"Building Industrial Mesh for Site: {site_id}")
        
        # Clear existing for this site instance if needed, or maintain map
        self.graph = nx.DiGraph() 
        
        # Load Assets
        for asset in site_data['assets']:
            self.graph.add_node(asset['id'], type=asset['type'], criticality=asset['criticality'])
            
        # Load Dependencies
        for u, v, w in site_data['dependencies']:
            self.graph.add_edge(u, v, coupling=w)
            
        logger.info(f"Site {site_id} mesh active with {self.graph.number_of_nodes()} nodes.")

    def set_asset_risk(self, asset_id: str, local_failure_prob: float):
        """
        Update local risk based on Layer 2 AI outputs.
        """
        self.asset_risks[asset_id] = local_failure_prob

    def propagate_cascading_risk(self) -> Dict[str, float]:
        """
        Propagate failure probabilities through the topological sort of the graph.
        P(B_fail) = P(B_local) + (P(A_fail) * Coupling(A, B))
        """
        # Initialize probabilities
        joint_probabilities = {node: self.asset_risks.get(node, 0.01) for node in self.graph.nodes()}
        
        # Sort topologicaly for ordered propagation (since its a DAG)
        try:
            order = list(nx.topological_sort(self.graph))
        except nx.NetworkXUnfeasible:
            logger.error("Cyclic dependency detected in OT mesh. Propagation aborted.")
            return joint_probabilities

        for node in order:
            # P(node fails) = Local Hazard + Contribution from upstream failures
            upstream_nodes = list(self.graph.predecessors(node))
            if not upstream_nodes:
                continue
                
            incoming_risk = 1.0
            for up in upstream_nodes:
                # Bayesian style probability aggregation (Simplified)
                # Prob of not failing = Product of (1 - individual upstream failure contribution)
                coupling = self.graph[up][node]['coupling']
                incoming_risk *= (1 - (joint_probabilities[up] * coupling))
            
            # Final Risk = 1 - (Success_Local * Success_Incoming)
            local_success = 1 - joint_probabilities[node]
            node_success = local_success * incoming_risk
            joint_probabilities[node] = float(np.clip(1 - node_success, 0.0, 1.0))

        logger.info("Bayesian Cascading Risk Calculation: SUCCESS")
        return joint_probabilities

    def get_root_cause_ranking(self, target_node: str) -> List[Dict[str, Any]]:
        """
        Identify which upstream node is contributing the most to target_node risk.
        Equivalent to Causal Attribution / Explainability.
        """
        if target_node not in self.graph:
            return []
            
        predecessors = list(self.graph.predecessors(target_node))
        rankings = []
        for p in predecessors:
            contribution = joint_probabilities.get(p, 0) * self.graph[p][target_node]['coupling']
            rankings.append({"source": p, "contribution": contribution})
            
        return sorted(rankings, key=lambda x: x['contribution'], reverse=True)

if __name__ == "__main__":
    engine = CausalBayesianEngine()
    engine.initialize_infrastructure_mesh()
    
    # Set high risk on the filter (Layer 2 predicted storm impact)
    engine.set_asset_risk("PRIMARY_FILTER", 0.75) 
    
    joint_risks = engine.propagate_cascading_risk()
    print("Cross-Asset Risk Map:")
    for asset, risk in joint_risks.items():
        print(f" - {asset}: {risk:.4f}")
