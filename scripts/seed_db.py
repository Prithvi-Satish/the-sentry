import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from src.database import init_db, get_db_connection
from simulate_stream import generate_mock_stream

def seed_database():
    print("1. Initializing Database Schema...")
    init_db()
    
    print("2. Generating 50 varied mock transactions...")
    transactions = generate_mock_stream(50)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("3. Seeding 'transactions' and 'feature_store' tables...")
    for txn in transactions:
        # Insert or ignore into Feature Store (assuming 1 state per customer)
        cursor.execute('''
            INSERT OR REPLACE INTO feature_store 
            (customer_id, is_i4c_hit, rolling_30d_volume, velocity_60m_count, 
             device_fingerprint_match, is_new_payee, is_out_of_state, 
             is_dormant_account, is_fan_out, has_shared_contact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            txn.customer_id, txn.is_i4c_hit, txn.rolling_30d_volume, txn.velocity_60m_count,
            txn.device_fingerprint_match, txn.is_new_payee, txn.is_out_of_state,
            txn.is_dormant_account, txn.is_fan_out, txn.has_shared_contact
        ))

        # Insert raw transaction
        cursor.execute('''
            INSERT INTO transactions 
            (transaction_id, customer_id, origin_account, destination_account, 
             amount, currency, timestamp, destination_country, current_ip, 
             current_ip_country, device_id, channel)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            txn.transaction_id, txn.customer_id, txn.origin_account, txn.destination_account,
            txn.amount, txn.currency, txn.timestamp.isoformat(), txn.destination_country, 
            txn.current_ip, txn.current_ip_country, txn.device_id, txn.channel
        ))
        
    conn.commit()
    conn.close()
    
    print("[+] Database successfully seeded!")
    print("-> Data saved natively inside 'sentry.db'")

if __name__ == "__main__":
    seed_database()
