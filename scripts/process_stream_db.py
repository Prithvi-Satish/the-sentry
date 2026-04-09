import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db_connection
from src.sentry import TheSentry
from src.schemas import TransactionParams
from datetime import datetime

def run_sentry_stream():
    print("=== THE SENTRY : Starting DB Stream Processor ===")
    sentry = TheSentry()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch all unprocessed transactions from SQLite
    cursor.execute("SELECT * FROM transactions WHERE status = 'PENDING'")
    raw_txns = cursor.fetchall()
    
    print(f"[*] Found {len(raw_txns)} transactions pending processing in SQLite stream.\n")
    
    alerts_generated = 0
    
    for row in raw_txns:
        txn_data = dict(row)
        customer_id = txn_data['customer_id']
        txn_id = txn_data['transaction_id']
        
        # 2. Fetch the corresponding variables from the Feature Store
        cursor.execute("SELECT * FROM feature_store WHERE customer_id = ?", (customer_id,))
        feature_data = dict(cursor.fetchone() or {})
        
        # Merge dictionaries resolving any overlaps
        # and cast timestamps back
        # Since we use ISO strings in SQLite, Pydantic handles parsing
        combined = {**txn_data, **feature_data}
        
        # Instantiate clean Schema
        try:
            txn_param = TransactionParams(**combined)
        except Exception as e:
            print(f"Error parsing transaction {txn_id}: {e}")
            continue
            
        # 3. Process via The Sentry
        alert_output = sentry.process_transaction(txn_param)
        
        # Mark as processed
        cursor.execute("UPDATE transactions SET status = 'PROCESSED' WHERE transaction_id = ?", (txn_id,))
        
        # 4. Save JSON Schema to table if an alert was generated
        if alert_output:
            alerts_generated += 1
            band = alert_output.alert_summary.anomaly_band
            json_blob = alert_output.model_dump_json()
            
            cursor.execute('''
                INSERT INTO alerts (transaction_id, customer_id, anomaly_band, alert_json_payload)
                VALUES (?, ?, ?, ?)
            ''', (txn_id, customer_id, band, json_blob))
            
            print(f"🚨 [STORED] Database Intercept -> TXN: {txn_id} | Band: {band}")
        else:
            print(f"✅ [PASSED] Clean Transaction  -> TXN: {txn_id}")
            
    conn.commit()
    conn.close()
    
    print(f"\n[+] Processing finished. {alerts_generated} Alerts natively pushed into 'alerts' SQLite table.")

if __name__ == "__main__":
    run_sentry_stream()
