import pytest
import json
from datetime import datetime, timezone
from src.schemas import TransactionParams, AnomalyBand, ResearcherOutput
from src.sentry import TheSentry

@pytest.fixture
def base_txn():
    return TransactionParams(
        transaction_id="TXN-123456",
        customer_id="CUST-9999",
        origin_account="ACCT-1111",
        destination_account="ACCT-2222",
        amount=50000.0,
        currency="INR",
        timestamp=datetime.now(timezone.utc),
        destination_country="IN",
        current_ip="192.168.1.1",
        current_ip_country="IN",
        device_id="DEV-001",
        channel="UPI",
        # Features
        is_i4c_hit=False,
        rolling_30d_volume=50000.0,
        velocity_60m_count=1,
        device_fingerprint_match=True,
        is_new_payee=False,
        is_out_of_state=False,
        is_dormant_account=False,
        is_fan_out=False,
        has_shared_contact=False
    )

def test_pass_transaction(base_txn):
    sentry = TheSentry()
    output = sentry.process_transaction(base_txn)
    # Basic transaction should PASS and return None
    assert output is None

def test_i4c_hit_critical(base_txn):
    base_txn.is_i4c_hit = True
    sentry = TheSentry()
    output = sentry.process_transaction(base_txn)
    
    assert output is not None
    assert output.alert_summary.anomaly_band == AnomalyBand.CRITICAL.value
    assert output.auto_blocked is True
    reason_codes = [rc.code for rc in output.alert_summary.reason_codes]
    assert "RC-000" in reason_codes

def test_structuring_detection(base_txn):
    base_txn.amount = 950000 # Under 10L
    base_txn.velocity_60m_count = 4 # High velocity
    sentry = TheSentry()
    output = sentry.process_transaction(base_txn)
    
    assert output is not None
    assert output.alert_summary.risk_score >= 0.50 # Structuring is weight 0.50
    reason_codes = [rc.code for rc in output.alert_summary.reason_codes]
    assert "RC-012" in reason_codes

def test_adversarial_probe_guardrail(base_txn):
    # Score between 0.60 and 0.70
    base_txn.amount = 5100000 # Provokes RC-003 (>50L rolling, weight 0.60)
    sentry = TheSentry()
    
    # 5 transactions should not trigger the flag
    for i in range(5):
        txn = base_txn.model_copy()
        txn.transaction_id = f"TXN-10{i}"
        output = sentry.process_transaction(txn)
        # Verify it's medium or high band and no guardrail yet
        assert output is not None
        assert "GR-001" not in [rc.code for rc in output.alert_summary.reason_codes]
        
    # The 6th transaction for the same customer should trip the guardrail
    output_6 = sentry.process_transaction(base_txn)
    reason_codes = [rc.code for rc in output_6.alert_summary.reason_codes]
    assert "GR-001" in reason_codes
    assert output_6.alert_summary.risk_score >= 0.75

def test_output_schema(base_txn):
    base_txn.is_i4c_hit = True
    sentry = TheSentry()
    output = sentry.process_transaction(base_txn)
    
    json_str = output.model_dump_json()
    assert "case_metadata" in json_str
    assert "trigger_source" in json_str
    
    # Verify we can strictly parse it back into the schema
    parsed = ResearcherOutput.model_validate_json(json_str)
    assert parsed.case_metadata.customer_id == "CUST-9999"
