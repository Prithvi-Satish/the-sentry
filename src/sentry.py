import uuid
from datetime import datetime, timezone
from typing import Optional, Dict

from src.schemas import (
    TransactionParams, ResearcherOutput, CaseMetadata, 
    AlertSummary, TriggerContext, FlaggedTransaction, 
    AnomalyBand, AlertType, ReasonCode
)
from src.layers.rules_engine import RulesEngine
from src.layers.ml_anomaly import MLAnomalyLayer
from src.layers.vector_matcher import VectorMatcherLayer

class TheSentry:
    def __init__(self):
        self.rules_engine = RulesEngine()
        self.ml_layer = MLAnomalyLayer()
        self.vector_layer = VectorMatcherLayer()
        
        # In-memory store for Adversarial Probe Detection
        # Maps customer_id -> count of near-threshold transactions (0.60 to 0.70)
        self.probe_tracking: Dict[str, int] = {}
        
    def process_transaction(self, txn: TransactionParams) -> Optional[ResearcherOutput]:
        """
        Processes a transaction stream event.
        Returns a ResearcherOutput compliant JSON structure if anomaly_band >= LOW.
        If PASS, returns None (logged but not dispatched).
        """
        # 1. Evaluate layers (Simulating concurrent execution)
        base_score, rules_reasons = self.rules_engine.evaluate(txn)
        ml_additive, ml_reasons = self.ml_layer.evaluate(txn)
        vector_additive, vector_reasons = self.vector_layer.evaluate(txn)
        
        # 2. Composite Score
        total_score = base_score + ml_additive + vector_additive
        risk_score = min(1.0, max(0.0, total_score))
        
        all_reasons = rules_reasons + ml_reasons + vector_reasons
        
        # 3. Guardrail: Adversarial Probe Detection
        if 0.60 <= risk_score <= 0.70:
            count = self.probe_tracking.get(txn.customer_id, 0) + 1
            self.probe_tracking[txn.customer_id] = count
            if count > 5:
                # Flag as probe
                risk_score = max(risk_score, 0.75) # Elevate risk score
                all_reasons.append(ReasonCode(
                    code="GR-001", 
                    description="Adversarial Probe Detection (>5 near-threshold txns)"
                ))
        
        # 4. Anomaly Band Determination
        if risk_score > 0.85 or txn.is_i4c_hit:
            band = AnomalyBand.CRITICAL
        elif risk_score >= 0.65:
            band = AnomalyBand.HIGH
        elif risk_score >= 0.50:
            band = AnomalyBand.MEDIUM
        elif risk_score >= 0.30:
            band = AnomalyBand.LOW
        else:
            band = AnomalyBand.PASS
            
        # Zero-Verdict Policy: Only log if PASS
        if band == AnomalyBand.PASS:
            # Here we would just log to Kafka/DB and return None
            return None
            
        # 5. Output Construction
        auto_block = True if (txn.is_i4c_hit or band == AnomalyBand.CRITICAL) else False
        
        # Determine primary alert type based on reasons
        alert_type = AlertType.MULTI_LAYER_ANOMALY.value
        if any(r.code == "RC-000" for r in all_reasons):
            alert_type = AlertType.I4C_HIT.value
        elif any(r.code == "RC-012" for r in all_reasons):
            alert_type = AlertType.STRUCTURING_DETECTED.value
        elif any(r.code == "RC-004" for r in all_reasons):
            alert_type = AlertType.VELOCITY_BREACH.value
            
        output = ResearcherOutput(
            case_metadata=CaseMetadata(
                case_id=f"CASE-{uuid.uuid4()}",
                alert_id=f"ALT-{uuid.uuid4()}",
                customer_id=txn.customer_id,
                transaction_id=txn.transaction_id,
                created_at=datetime.now(timezone.utc).isoformat()
            ),
            trigger_source="RULE_ENGINE_V1",
            alert_summary=AlertSummary(
                alert_type=alert_type,
                risk_score=round(risk_score, 2),
                model_name="Sentry_Composite_V1",
                model_version="1.0.0",
                anomaly_band=band.value,
                reason_codes=all_reasons
            ),
            trigger_context=TriggerContext(
                current_ip=txn.current_ip,
                current_ip_country=txn.current_ip_country,
                device_id=txn.device_id,
                shared_email=txn.shared_email,
                shared_phone=txn.shared_phone,
                channel=txn.channel
            ),
            flagged_transaction=FlaggedTransaction(
                origin_account=txn.origin_account,
                destination_account=txn.destination_account,
                amount=txn.amount,
                currency=txn.currency,
                timestamp=txn.timestamp.isoformat(),
                destination_country=txn.destination_country
            ),
            auto_blocked=auto_block
        )
        
        return output
