import sqlite3
import hashlib
import datetime
import os
import pandas as pd
import streamlit as st

DB_PATH = "user_access.db"

def _hash_password(password: str) -> str:
    """Returns SHA-256 hash of the password with salt."""
    salt = "ecm_opera_house_2026_salt"
    return hashlib.sha256(f"{salt}{password}".encode('utf-8')).hexdigest()

def init_auth_db():
    """Initializes SQLite database for user credentials and access audit logging."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    """)
    
    # 2. Access logs table
    c.execute("""
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT,
            access_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            access_date DATE NOT NULL,
            access_month TEXT NOT NULL
        )
    """)

    # 3. IP persistent sessions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS ip_sessions (
            ip_address TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            email TEXT,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    
    # Ensure default admin user: uzair087 / uza0809
    c.execute("SELECT username FROM users WHERE username = 'uzair087'")
    admin_exists = c.fetchone()
    if not admin_exists:
        c.execute("""
            INSERT INTO users (username, email, password_hash, role, is_active)
            VALUES (?, ?, ?, ?, ?)
        """, ('uzair087', 'uzair.ahmad@ecm-jv.com', _hash_password('uza0809'), 'admin', 1))
        conn.commit()
        
    conn.close()

def get_client_ip():
    """Extracts client IP address reliably from Streamlit context or HTTP headers."""
    try:
        # Check Streamlit 1.35+ st.context.ip_address
        if hasattr(st, "context") and hasattr(st.context, "ip_address") and st.context.ip_address:
            return str(st.context.ip_address).strip()
        # Check headers for X-Forwarded-For or remote IP
        if hasattr(st, "context") and hasattr(st.context, "headers") and st.context.headers:
            headers = st.context.headers
            for key in ["x-forwarded-for", "X-Forwarded-For", "x-real-ip", "X-Real-IP"]:
                if key in headers and headers[key]:
                    return str(headers[key]).split(",")[0].strip()
    except Exception:
        pass
    return "127.0.0.1"

def save_ip_session(ip_address: str, user_dict: dict):
    """Saves or updates persistent session for client IP."""
    if not ip_address or not user_dict:
        return
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO ip_sessions (ip_address, username, role, email, last_seen)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(ip_address) DO UPDATE SET
            username=excluded.username,
            role=excluded.role,
            email=excluded.email,
            last_seen=CURRENT_TIMESTAMP
    """, (ip_address.strip(), user_dict.get("username", ""), user_dict.get("role", "viewer"), user_dict.get("email", "")))
    conn.commit()
    conn.close()

def get_user_by_ip(ip_address: str):
    """Retrieves active user session for client IP if recognized."""
    if not ip_address:
        return False, None
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT s.username, s.role, s.email 
        FROM ip_sessions s
        JOIN users u ON LOWER(u.username) = LOWER(s.username)
        WHERE s.ip_address = ? AND u.is_active = 1
    """, (ip_address.strip(),))
    row = c.fetchone()
    conn.close()
    if row:
        return True, {
            "username": row[0],
            "role": row[1],
            "email": row[2]
        }
    return False, None

def clear_ip_session(ip_address: str):
    """Clears saved session for client IP on sign out."""
    if not ip_address:
        return
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM ip_sessions WHERE ip_address = ?", (ip_address.strip(),))
    conn.commit()
    conn.close()

def authenticate_user(username_or_email: str, password: str):
    """Verifies user credentials. Returns (bool, user_dict)."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT username, email, password_hash, role, is_active 
        FROM users 
        WHERE (LOWER(username) = LOWER(?) OR LOWER(email) = LOWER(?)) AND is_active = 1
    """, (username_or_email.strip(), username_or_email.strip()))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return False, None
        
    stored_hash = row[2]
    if stored_hash == _hash_password(password.strip()):
        user_info = {
            "username": row[0],
            "email": row[1],
            "role": row[3]
        }
        return True, user_info
    return False, None

def generate_remember_token(username: str) -> str:
    """Generates a verifiable persistent token for the Remember Me feature."""
    secret_salt = "ecm_remember_me_token_salt_2026"
    sig = hashlib.sha256(f"{username}:{secret_salt}".encode('utf-8')).hexdigest()
    return f"{username}_{sig[:16]}"

def verify_remember_token(token: str):
    """Verifies a remember me token and returns (bool, user_dict)."""
    if not token or "_" not in token:
        return False, None
    parts = token.split("_")
    if len(parts) != 2:
        return False, None
    username, sig = parts
    expected_token = generate_remember_token(username)
    if token == expected_token:
        init_auth_db()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT username, email, role, is_active FROM users WHERE LOWER(username) = LOWER(?) AND is_active = 1", (username.strip(),))
        row = c.fetchone()
        conn.close()
        if row:
            return True, {
                "username": row[0],
                "email": row[1],
                "role": row[2]
            }
    return False, None

def log_user_access(username: str, email: str = ""):
    """Logs a successful access event with date and month grouping."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today_str = datetime.date.today().isoformat()
    month_str = datetime.date.today().strftime("%Y-%m")
    c.execute("""
        INSERT INTO access_logs (username, email, access_date, access_month)
        VALUES (?, ?, ?, ?)
    """, (username, email, today_str, month_str))
    conn.commit()
    conn.close()

def add_user(username: str, email: str, password: str, role: str = 'viewer'):
    """Adds or updates a user in the database."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    pwd_hash = _hash_password(password.strip())
    try:
        c.execute("""
            INSERT INTO users (username, email, password_hash, role, is_active)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(username) DO UPDATE SET
                email=excluded.email,
                password_hash=excluded.password_hash,
                role=excluded.role,
                is_active=1
        """, (username.strip().lower(), email.strip().lower(), pwd_hash, role))
        conn.commit()
        success = True
        msg = f"User '{username}' registered successfully."
    except Exception as e:
        success = False
        msg = f"Error creating user: {e}"
    conn.close()
    return success, msg

def get_all_users_df():
    """Returns a pandas DataFrame of all registered users."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT username, email, role, created_at, is_active FROM users ORDER BY created_at DESC", conn)
    conn.close()
    return df

def delete_user(username: str):
    """Deletes a user from the system."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def get_access_stats():
    """Returns summarized access stats per user, per day, and per month."""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    
    # Total access count per user
    user_counts = pd.read_sql_query("""
        SELECT username, email, 
               COUNT(*) as total_logins,
               MAX(access_time) as last_access
        FROM access_logs 
        GROUP BY username, email
        ORDER BY total_logins DESC
    """, conn)
    
    # Access count per user per day
    daily_counts = pd.read_sql_query("""
        SELECT access_date, username, email, COUNT(*) as login_count
        FROM access_logs
        GROUP BY access_date, username, email
        ORDER BY access_date DESC, login_count DESC
    """, conn)
    
    # Access count per user per month
    monthly_counts = pd.read_sql_query("""
        SELECT access_month, username, email, COUNT(*) as login_count
        FROM access_logs
        GROUP BY access_month, username, email
        ORDER BY access_month DESC, login_count DESC
    """, conn)
    
    # Raw log history
    recent_logs = pd.read_sql_query("""
        SELECT id, username, email, access_time, access_date, access_month
        FROM access_logs
        ORDER BY id DESC LIMIT 150
    """, conn)
    
    conn.close()
    return user_counts, daily_counts, monthly_counts, recent_logs
