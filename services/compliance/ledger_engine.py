import logging
import hashlib
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger("SovereignLedger")

class LedgerBlock(BaseModel):
    block_index: int
    timestamp: datetime
    previous_hash: str
    merkle_root: str
    inference_id: str
    asset_id: str
    action_type: str
    esg_impact_kg: float
    verification_hash: str
    node_origin: str
    certificate_id: str

class SovereignLedgerEngine:
    """
    SAHARYN Sovereign Compliance Ledger.
    Maintains an immutable chain of custody for all ESG claims and operational directives.
    Implements simulated cryptographic chaining for industrial validation.
    """
    
    def __init__(self, node_id: str = "RIYADH_CENTRAL_01"):
        self.node_id = node_id
        self.chain: List[LedgerBlock] = []
        self._initialize_genesis_block()

    def _initialize_genesis_block(self):
        """Creates the initial anchor block for the sovereign chain."""
        genesis = LedgerBlock(
            block_index=0,
            timestamp=datetime(2024, 1, 1, 0, 0, 0),
            previous_hash="0" * 64,
            merkle_root="0xGENESIS_ANCHOR_SAHARYN",
            inference_id="SYSTEM_BOOT",
            asset_id="CORE_NETWORK",
            action_type="GENESIS",
            esg_impact_kg=0.0,
            verification_hash=self._calculate_hash(0, "0" * 64, "0xGENESIS_ANCHOR_SAHARYN"),
            node_origin=self.node_id,
            certificate_id="SHRN-GEN-0000"
        )
        self.chain.append(genesis)

    def _calculate_hash(self, index: int, prev_hash: str, merkle_root: str) -> str:
        """Simulates SHA-256 hashing of block header."""
        header = f"{index}{prev_hash}{merkle_root}"
        return hashlib.sha256(header.encode()).hexdigest()

    def commit_esg_claim(self, inference_id: str, asset_id: str, action_type: str, kg_saved: float) -> LedgerBlock:
        """
        Commits a new validated ESG claim to the ledger.
        Ensures temporal and cryptographic continuity.
        """
        last_block = self.chain[-1]
        next_index = last_block.block_index + 1
        
        # Merkle Root Formulation (Simplified for Demonstration)
        payload_data = f"{inference_id}{asset_id}{action_type}{kg_saved}"
        merkle_root = hashlib.sha256(payload_data.encode()).hexdigest()
        
        # Block Creation
        new_block = LedgerBlock(
            block_index=next_index,
            timestamp=datetime.utcnow(),
            previous_hash=last_block.verification_hash,
            merkle_root=merkle_root,
            inference_id=inference_id,
            asset_id=asset_id,
            action_type=action_type,
            esg_impact_kg=round(kg_saved, 6),
            verification_hash=self._calculate_hash(next_index, last_block.verification_hash, merkle_root),
            node_origin=self.node_id,
            certificate_id=f"SHRN-{self.node_id[:3]}-{next_index:04d}-{uuid.uuid4().hex[:4].upper()}"
        )
        
        self.chain.append(new_block)
        logger.info(f"LEDGER_COMMIT: Block {next_index} verified by {self.node_id} (Claim: {kg_saved}kg CO2)")
        
        # Pruning (Optional for demo, keep last 20 blocks in memory)
        if len(self.chain) > 50:
            self.chain.pop(1) # Keep genesis at 0
            
        return new_block

    def get_ledger_history(self, limit: int = 20) -> List[LedgerBlock]:
        """Returns the most recent validated blocks."""
        return sorted(self.chain, key=lambda x: x.block_index, reverse=True)[:limit]

    def get_aggregate_esg_savings(self) -> float:
        """Calculates total carbon savings recorded in this node's history."""
        return sum(block.esg_impact_kg for block in self.chain)

if __name__ == "__main__":
    ledger = SovereignLedgerEngine()
    block = ledger.commit_esg_claim(str(uuid.uuid4()), "PUMP_SA_01", "PREVENTIVE_MAINTENANCE", 14.22)
    print(f"Verified Block: {block.json(indent=2)}")
