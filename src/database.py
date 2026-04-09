import sqlite3
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "sentry.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Raw Transactions Table (Simulating stream input)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT UNIQUE,
            customer_id TEXT,
            origin_account TEXT,
            destination_account TEXT,
            amount REAL,
            currency TEXT,
            timestamp TEXT,
            destination_country TEXT,
            current_ip TEXT,
            current_ip_country TEXT,
            device_id TEXT,
            channel TEXT,
            status TEXT DEFAULT 'PENDING'
        )
    ''')
    
    # 2. Mock Feature Store Table (Aggregates + Flags)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feature_store (
            customer_id TEXT PRIMARY KEY,
            is_i4c_hit BOOLEAN,
            rolling_30d_volume REAL,
            velocity_60m_count INTEGER,
            device_fingerprint_match BOOLEAN,
            is_new_payee BOOLEAN,
            is_out_of_state BOOLEAN,
            is_dormant_account BOOLEAN,
            is_fan_out BOOLEAN,
            has_shared_contact BOOLEAN
        )
    ''')
    
    # 3. Output Alerts Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT,
            customer_id TEXT,
            anomaly_band TEXT,
            alert_json_payload TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn
