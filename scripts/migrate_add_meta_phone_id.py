"""
Migration: Add meta_phone_number_id to businesses table.
Run once. Safe to re-run (uses ALTER TABLE IF NOT EXISTS pattern).
"""
import sqlite3

conn = sqlite3.connect('flowcore.db')
cur = conn.cursor()

# Check if column already exists
cur.execute("PRAGMA table_info(businesses)")
cols = [c[1] for c in cur.fetchall()]

if 'meta_phone_number_id' not in cols:
    cur.execute("ALTER TABLE businesses ADD COLUMN meta_phone_number_id VARCHAR(50) DEFAULT NULL")
    conn.commit()
    print("OK: Added column meta_phone_number_id")
else:
    print("SKIP: Column meta_phone_number_id already exists.")

# Verify
cur.execute("PRAGMA table_info(businesses)")
print("\nCurrent businesses columns:")
for c in cur.fetchall():
    print(f"  {c[1]} ({c[2]})")

conn.close()

