from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from enum import Enum

# ==========================================
# Input Schemas (Simulating Feature Store)
# ==========================================
class TransactionParams(BaseModel):
    transaction_id: str
    customer_id: str
    origin_account: str
    destination_account: str
    amount: float
    currency: str = "INR"
    timestamp: datetime
    destination_country: str
    
    # Context
    current_ip: str
    current_ip_country: str
    device_id: str
    shared_email: Optional[str] = None
    shared_phone: Optional[str] = None
    channel: str
    
    # Simulated Feature Store enrichments
    is_i4c_hit: bool = False
    rolling_30d_volume: float = 0.0
    velocity_60m_count: int = 0
    device_fingerprint_match: bool = True
    
    # New features from reason code list
    is_new_payee: bool = False
    is_out_of_state: bool = False
    is_dormant_account: bool = False
    is_fan_out: bool = False
    has_shared_contact: bool = False

# ==========================================
# Output Contract Schemas
# ==========================================
class AlertType(str, Enum):
    STRUCTURING_DETECTED = "STRUCTURING_DETECTED"
    VELOCITY_BREACH = "VELOCITY_BREACH"
    PMLA_THRESHOLD = "PMLA_THRESHOLD"
    I4C_HIT = "I4C_HIT"
    MULTI_LAYER_ANOMALY = "MULTI_LAYER_ANOMALY"

class AnomalyBand(str, Enum):
    PASS = "PASS"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ReasonCode(BaseModel):
    code: str
    description: str

class CaseMetadata(BaseModel):
    case_id: str
    alert_id: str
    customer_id: str
    transaction_id: str
    created_at: str

class AlertSummary(BaseModel):
    alert_type: str
    risk_score: float
    model_name: str
    model_version: str
    anomaly_band: str
    reason_codes: List[ReasonCode]

class TriggerContext(BaseModel):
    current_ip: str
    current_ip_country: str
    device_id: str
    shared_email: Optional[str] = None
    shared_phone: Optional[str] = None
    channel: str

class FlaggedTransaction(BaseModel):
    origin_account: str
    destination_account: str
    amount: float
    currency: str = "INR"
    timestamp: str
    destination_country: str

class ResearcherOutput(BaseModel):
    case_metadata: CaseMetadata
    trigger_source: str
    alert_summary: AlertSummary
    trigger_context: TriggerContext
    flagged_transaction: FlaggedTransaction
    auto_blocked: Optional[bool] = None
