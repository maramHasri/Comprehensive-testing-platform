"""
Run this to test database connection and see the exact error.
Usage: python scripts/check_db_connection.py
"""
import os
import sys

# Load .env from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("ERROR: DATABASE_URL is not set in .env")
    sys.exit(1)

# Hide password in print
import re
masked = re.sub(r":([^/@]+)@", ":****@", db_url)
print(f"Connecting to: {masked}")

from urllib.parse import urlparse
u = urlparse(db_url)
dbname = u.path.lstrip("/")

try:
    import psycopg2
    conn = psycopg2.connect(
        host=u.hostname,
        port=u.port or 5432,
        dbname=u.path.lstrip("/"),
        user=u.username,
        password=u.password,
    )
    conn.close()
    print("OK: Database connection successful.")
except Exception as e:
    print(f"ERROR: {e}")
    if "does not exist" in str(e):
        print("\nFix: Create the database in pgAdmin (or run in psql):")
        print(f'  CREATE DATABASE "{dbname}";')
    elif "connection refused" in str(e).lower() or "could not connect" in str(e).lower():
        print("\nFix: Start PostgreSQL service and ensure it listens on the given host/port.")
    sys.exit(1)
