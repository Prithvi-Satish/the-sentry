import numpy as np
from src.schemas import TransactionParams, ReasonCode
from typing import Tuple, List

class VectorMatcherLayer:
    def __init__(self):
        # Simulating stored FIU-IND typology embeddings
        # A real implementation would use SentenceTransformers + a VectorDB
        np.random.seed(42)
        # Normalised random vectors
        vecs = np.random.rand(5, 16)
        self.typology_vectors = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
        
    def _extract_embedding(self, txn: TransactionParams) -> np.ndarray:
        # Dummy encoder returning a 16-D normalized vector based on transaction heuristics
        val = min(1.0, txn.amount / 1_000_000)
        vec = np.full(16, val)
        # Add some variation
        vec[0] = txn.velocity_60m_count / 10.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def evaluate(self, txn: TransactionParams) -> Tuple[float, List[ReasonCode]]:
        """
        Simulates vector lookup for known fraud typologies via cosine similarity.
        """
        embedding = self._extract_embedding(txn)
        
        similarities = np.dot(self.typology_vectors, embedding)
        max_sim = np.max(similarities)
        
        risk_additive = 0.0
        reasons = []

        if max_sim > 0.90:
            risk_additive = 0.20
            reasons.append(ReasonCode(code="RC-006", description="High vector similarity to known fraud pattern"))
        elif max_sim > 0.75:
            risk_additive = 0.05
            reasons.append(ReasonCode(code="RC-006", description="Moderate vector similarity to known fraud pattern"))

        return risk_additive, reasons
