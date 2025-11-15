"""
Simple test to check Supabase connectivity with raw psycopg2
"""
import psycopg2
from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env
load_dotenv(Path.cwd() / '.env')

USER = os.getenv("user")
PASSWORD = os.getenv("password")
HOST = os.getenv("host")
PORT = os.getenv("port")
DBNAME = os.getenv("dbname")

print(f"Connecting to: {USER}@{HOST}:{PORT}/{DBNAME}")
print(f"Password length: {len(PASSWORD) if PASSWORD else 0}")

try:
    print("\n🔧 Attempting connection...")
    connection = psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME,
        connect_timeout=10
    )
    print("✅ Connection successful!")
    
    cursor = connection.cursor()
    cursor.execute("SELECT NOW();")
    result = cursor.fetchone()
    print(f"✅ Current Time from DB: {result[0]}")

    cursor.close()
    connection.close()
    print("✅ Connection closed cleanly.")

except psycopg2.OperationalError as e:
    print(f"❌ Connection failed (OperationalError): {e}")
    print("\nPossible causes:")
    print("  1. Database is paused (free tier auto-pauses after inactivity)")
    print("  2. Firewall blocking connection")
    print("  3. Incorrect credentials")
    print("\n👉 Check Supabase dashboard - database might be paused!")
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
