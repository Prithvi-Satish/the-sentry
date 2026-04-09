import numpy as np
from sklearn.ensemble import IsolationForest
from src.schemas import TransactionParams, ReasonCode
from typing import Tuple, List

class MLAnomalyLayer:
    def __init__(self):
        # Instantiate a basic Isolation Forest. In production, load from model registry.
        self.model = IsolationForest(contamination=0.01, random_state=42)
        # Dummy fit so it's ready to predict
        # Features: [amount, 30d_volume, 60m_velocity]
        dummy_data = np.array([
            [1000, 5000, 1],
            [2000, 10000, 2],
            [500, 2000, 1],
            [100000, 200000, 5]
        ])
        self.model.fit(dummy_data)

    def evaluate(self, txn: TransactionParams) -> Tuple[float, List[ReasonCode]]:
        """
        Runs Isolation Forest to detect statistical outliers.
        Returns a risk score additive (0.0 to 0.3) and reason codes.
        """
        features = np.array([[txn.amount, txn.rolling_30d_volume, txn.velocity_60m_count]])
        
        # IF returns negative anomaly scores (lower is more anomalous)
        anomaly_score = self.model.score_samples(features)[0]
        
        risk_additive = 0.0
        reasons = []

        if anomaly_score < -0.6:
            risk_additive = 0.25 # Max additive
            reasons.append(ReasonCode(code="RC-005", description="ML anomaly score above threshold (High)"))
        elif anomaly_score < -0.4:
            risk_additive = 0.10
            reasons.append(ReasonCode(code="RC-005", description="ML anomaly score above threshold (Moderate)"))

        return risk_additive, reasons
