import oracledb
import os
from pathlib import Path

# Paths
wallet_dir = str(Path(__file__).parent / "wallet")
password = "StrongPassword123!"  # Password used when generating the wallet
dsn = "brooksdb_low"

try:
    print(f"Connecting to Oracle ADB with wallet at: {wallet_dir}")
    conn = oracledb.connect(
        user="admin",
        password=password,
        dsn=dsn,
        config_dir=wallet_dir,
        wallet_location=wallet_dir,
        wallet_password=password
    )
    print("SUCCESS: Connected to Oracle Autonomous Database!")
    print(f"Server Version: {conn.version}")
    
    cursor = conn.cursor()
    cursor.execute("SELECT sysdate FROM dual")
    res = cursor.fetchone()
    print(f"Current DB Date: {res[0]}")
    
    conn.close()
except Exception as e:
    print(f"ERROR: Failed to connect to Oracle ADB: {e}")
