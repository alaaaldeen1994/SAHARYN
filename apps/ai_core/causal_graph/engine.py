import numpy as np
import networkx as nx
from typing import Dict, List, Any, Optional
from core.common.base import get_logger

class IndustrialCausalEngine:
    """
    Advanced Causal Graph for Industrial Systems.
    Uses adjacency matrix propagation to model cascading risks across interconnected assets.
    """
    def __init__(self):
        self.logger = get_logger("IndustrialCausalEngine")
        self.assets = {}
        self.graph = nx.DiGraph()
        self.adjacency_matrix = None
        self.asset_mapping = {} # ID -> Index for matrix operations

    def register_asset(self, asset_id: str, capacity: float, criticality: float):
        self.assets[asset_id] = {"capacity": capacity, "criticality": criticality}
        if asset_id not in self.asset_mapping:
            self.asset_mapping[asset_id] = len(self.asset_mapping)
        self.graph.add_node(asset_id)

    def define_interaction(self, source_id: str, target_id: str, coupling_strength: float):
        """
        Defines a functional dependency. 
        Coupling strength (0-1) represents how much a failure in source impacts performance in target.
        """
        self.graph.add_edge(source_id, target_id, weight=coupling_strength)
        self._sync_matrix()

    def _sync_matrix(self):
        n = len(self.asset_mapping)
        if n == 0: return
        self.adjacency_matrix = np.zeros((n, n))
        for u, v, d in self.graph.edges(data=True):
            self.adjacency_matrix[self.asset_mapping[u], self.asset_mapping[v]] = d['weight']

    def compute_cascading_failure(self, primary_failures: Dict[str, float]) -> Dict[str, float]:
        """
        Propagates failure probabilities using matrix exponentiation (steady-state reachability).
        P_final = (I - A)^-1 * P_initial
        """
        n = len(self.asset_mapping)
        if n == 0: return primary_failures
        
        # P vector initialization
        p_initial = np.zeros(n)
        for aid, prob in primary_failures.items():
            if aid in self.asset_mapping:
                p_initial[self.asset_mapping[aid]] = prob
        
        # Leontief inverse style propagation for dependency chains
        # We cap the spectral radius to ensure convergence if cycles exist
        I = np.eye(n)
        try:
            # P_total = P_initial + A*P_initial + A^2*P_initial ...
            # We use a finite sum for industrial stability (usually max depth 5-10)
            p_total = p_initial.copy()
            p_current = p_initial.copy()
            for _ in range(5):
                p_current = self.adjacency_matrix @ p_current
                p_total += p_current
        except Exception as e:
            self.logger.error(f"Matrix propagation failed: {e}")
            return primary_failures

        # Map back to IDs and normalize to [0, 1]
        results = {}
        for aid, idx in self.asset_mapping.items():
            results[aid] = float(np.clip(p_total[idx], 0.0, 1.0))
        
        return results

    def get_topological_risk_order(self) -> List[str]:
        """Returns assets sorted by their potential to cause downstream failure."""
        pagerank = nx.pagerank(self.graph, weight='weight')
        return sorted(pagerank, key=pagerank.get, reverse=True)
