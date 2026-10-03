import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auto_logs', 'ncr_status_overrides.db')

def init_ncr_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ncr_status_overrides (
            doc_no TEXT PRIMARY KEY,
            current_status TEXT,
            updated_by TEXT,
            updated_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_ncr_status_overrides():
    init_ncr_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT doc_no, current_status, updated_by, updated_at FROM ncr_status_overrides')
    rows = cursor.fetchall()
    conn.close()
    return {r[0]: {'current_status': r[1], 'updated_by': r[2], 'updated_at': r[3]} for r in rows}

def save_ncr_status_override(doc_no, current_status, updated_by="Team Member"):
    init_ncr_db()
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        INSERT INTO ncr_status_overrides (doc_no, current_status, updated_by, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(doc_no) DO UPDATE SET
            current_status = excluded.current_status,
            updated_by = excluded.updated_by,
            updated_at = excluded.updated_at
    ''', (doc_no.strip(), current_status.strip(), updated_by.strip(), datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_ncr_db()
    print("NCR overrides DB initialized successfully at:", DB_PATH)
