from typing import List, Tuple
from src.schemas import TransactionParams, ReasonCode

class RulesEngine:
    def __init__(self):
        # Weights as per specification
        self.weights = {
            "RC_000": 1.0,   # I4C Registry Hit
            "RC_001": 0.30,  # New payee + high value
            "RC_002": 0.45,  # PMLA Single Threshold (> ₹10L)
            "RC_003": 0.60,  # PMLA Rolling Threshold (> ₹50L)  
            "RC_004": 0.40,  # Velocity Breach (>10 UPI txns/hr)
            "RC_007": 0.25,  # Location anomaly (out-of-state + high value)
            "RC_008": 0.25,  # SIM/Device Mismatch
            "RC_009": 0.35,  # Dormant account sudden activity
            "RC_010": 0.40,  # Fan-out pattern detected
            "RC_011": 0.30,  # Shared phone/email across accounts
            "RC_012": 0.50   # Structuring Detection
        }

    def evaluate(self, txn: TransactionParams) -> Tuple[float, List[ReasonCode]]:
        """
        Evaluates the transaction against statutory thresholds and rules.
        Returns the composed risk score from Layer 1 and the list of reason codes.
        """
        score = 0.0
        reasons = []

        # RC-000: I4C Registry Hit
        if txn.is_i4c_hit:
            score += self.weights["RC_000"]
            reasons.append(ReasonCode(code="RC-000", description="I4C registry hit (auto-block)"))

        # RC-001: New payee + high value (e.g. > 1 Lakh)
        if txn.is_new_payee and txn.amount > 100_000:
            score += self.weights["RC_001"]
            reasons.append(ReasonCode(code="RC-001", description="New payee + high value"))

        # RC-002: PMLA Single Threshold (> ₹10L)
        if txn.amount > 1_000_000:
            score += self.weights["RC_002"]
            reasons.append(ReasonCode(code="RC-002", description="Transaction > ₹10L single"))

        # RC-003: PMLA Rolling Threshold (> ₹50L)
        if txn.rolling_30d_volume + txn.amount > 5_000_000:
            score += self.weights["RC_003"]
            reasons.append(ReasonCode(code="RC-003", description="PMLA Rolling Threshold (> ₹50L)"))

        # RC-004: Velocity Breach (>10 UPI transactions in 60 minutes)
        if txn.channel.upper() == "UPI" and txn.velocity_60m_count > 10:
            score += self.weights["RC_004"]
            reasons.append(ReasonCode(code="RC-004", description="Velocity breach (N txns in T mins)"))

        # RC-007: Location anomaly (out-of-state + high value)
        if txn.is_out_of_state and txn.amount > 200_000:
            score += self.weights["RC_007"]
            reasons.append(ReasonCode(code="RC-007", description="Location anomaly (out-of-state + high value)"))

        # RC-008: SIM/Device Mismatch
        if not txn.device_fingerprint_match:
            score += self.weights["RC_008"]
            reasons.append(ReasonCode(code="RC-008", description="SIM / device mismatch"))

        # RC-009: Dormant account sudden activity
        if txn.is_dormant_account:
            score += self.weights["RC_009"]
            reasons.append(ReasonCode(code="RC-009", description="Dormant account sudden activity"))

        # RC-010: Fan-out pattern detected
        if txn.is_fan_out:
            score += self.weights["RC_010"]
            reasons.append(ReasonCode(code="RC-010", description="Fan-out pattern detected"))

        # RC-011: Shared phone/email across accounts
        if txn.has_shared_contact:
            score += self.weights["RC_011"]
            reasons.append(ReasonCode(code="RC-011", description="Shared phone / email across accounts"))

        # RC-012: Structuring Detection (Sub-threshold "smurfing")
        # Heuristic: amt between 9L and 10L (just below threshold) and high velocity
        if 900_000 <= txn.amount < 1_000_000 and txn.velocity_60m_count > 3:
            score += self.weights["RC_012"]
            reasons.append(ReasonCode(code="RC-012", description="Structuring detected (sub-threshold pattern)"))

        return score, reasons
