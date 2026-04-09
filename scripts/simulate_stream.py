import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import uuid
import json
from datetime import datetime, timezone, timedelta
from src.sentry import TheSentry
from src.schemas import TransactionParams

def generate_mock_stream(num_txns=50):
    txns = []
    base_time = datetime.now(timezone.utc)
    
    # Predefined "fraud actors" to force certain rules
    i4c_actor = "CUST-I4C-999"
    dormant_actor = "CUST-DORM-888"
    structuring_actor = "CUST-SMURF-777"
    velocity_actor = "CUST-FAST-666"
    fanout_actor = "CUST-FAN-555"

    for i in range(num_txns):
        # ~80% normal, ~20% fraudulent anomalies
        is_fraud = random.random() < 0.25
        
        # Base normal params
        amount = random.uniform(100, 50000)
        cust_id = f"CUST-NORM-{random.randint(1000, 9000)}"
        i4c = False
        dormant = False
        new_payee = False
        velocity = random.randint(1, 3)
        thirty_day = random.uniform(1000, 200000)
        channel = "UPI"
        out_of_state = False
        fan_out = False
        device_match = True
        
        if is_fraud:
            fraud_type = random.choice(["I4C", "DORMANT", "STRUCTURING", "VELOCITY", "FANOUT", "HIGH_VALUE", "DEVICE_MISMATCH"])
            
            if fraud_type == "I4C":
                cust_id = i4c_actor
                i4c = True
                amount = 25000
            elif fraud_type == "DORMANT":
                cust_id = dormant_actor
                dormant = True
                amount = 450000
            elif fraud_type == "STRUCTURING":
                cust_id = structuring_actor
                amount = random.uniform(910000, 990000)
                velocity = 5
            elif fraud_type == "VELOCITY":
                cust_id = velocity_actor
                velocity = 15
                amount = 8000
            elif fraud_type == "FANOUT":
                cust_id = fanout_actor
                fan_out = True
                amount = 80000
            elif fraud_type == "HIGH_VALUE":
                cust_id = f"CUST-WHALE-{random.randint(10,99)}"
                amount = random.uniform(1100000, 5000000) # Exceeds 10L single limit
                new_payee = True
                out_of_state = True
            elif fraud_type == "DEVICE_MISMATCH":
                device_match = False
                amount = 300000
                
        txn = TransactionParams(
            transaction_id=f"TXN-{uuid.uuid4().hex[:8].upper()}",
            customer_id=cust_id,
            origin_account=f"ACCT-{cust_id[-4:]}",
            destination_account=f"ACCT-{random.randint(1111,9999)}",
            amount=round(amount, 2),
            currency="INR",
            timestamp=base_time + timedelta(minutes=i),
            destination_country="IN",
            current_ip=f"192.168.1.{random.randint(1,255)}",
            current_ip_country="IN",
            device_id=f"DEV-{cust_id}",
            channel=channel,
            is_i4c_hit=i4c,
            rolling_30d_volume=round(thirty_day, 2),
            velocity_60m_count=velocity,
            device_fingerprint_match=device_match,
            is_new_payee=new_payee,
            is_out_of_state=out_of_state,
            is_dormant_account=dormant,
            is_fan_out=fan_out,
            has_shared_contact=False
        )
        txns.append(txn)
        
    return txns

def run_simulation():
    print("=== Generating 50 Mock Transactions ===")
    stream = generate_mock_stream(50)
    
    sentry = TheSentry()
    alerts = []
    
    print("=== Streaming Transactions through The Sentry ===")
    for idx, txn in enumerate(stream):
        output = sentry.process_transaction(txn)
        if output:
            alerts.append(output.model_dump())
            print(f"[{idx+1:02d}] 🚨 ALERT GENERATED -> ID: {txn.transaction_id} | Amount: ₹{txn.amount:,.2f} | Band: {output.alert_summary.anomaly_band}")
        else:
            print(f"[{idx+1:02d}] ✅ PASS -> ID: {txn.transaction_id} | Amount: ₹{txn.amount:,.2f}")
            
    # Dump alerts to JSON file
    output_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sentry_alerts.json")
    with open(output_file, "w") as f:
        json.dump(alerts, f, indent=2)
        
    print(f"\n[+] Simulation complete. {len(alerts)} anomalous transactions caught and saved to {output_file}")

if __name__ == "__main__":
    run_simulation()
