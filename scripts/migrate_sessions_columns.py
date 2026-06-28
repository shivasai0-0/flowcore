"""
Migration: Add missing columns to sessions table.
Adds: is_archived, locked_until, last_active_at
Safe to re-run (checks existing columns first).
"""
import sqlite3
from datetime import datetime

conn = sqlite3.connect('flowcore.db')
cur = conn.cursor()

cur.execute('PRAGMA table_info(sessions)')
existing = [c[1] for c in cur.fetchall()]
print('Existing columns:', existing)

# is_archived: boolean, default 0 (not archived)
if 'is_archived' not in existing:
    cur.execute('ALTER TABLE sessions ADD COLUMN is_archived INTEGER NOT NULL DEFAULT 0')
    print('ADDED: is_archived')
else:
    print('SKIP: is_archived')

# locked_until: datetime, nullable
if 'locked_until' not in existing:
    cur.execute('ALTER TABLE sessions ADD COLUMN locked_until DATETIME DEFAULT NULL')
    print('ADDED: locked_until')
else:
    print('SKIP: locked_until')

# last_active_at: datetime — backfill existing rows with current time
if 'last_active_at' not in existing:
    cur.execute('ALTER TABLE sessions ADD COLUMN last_active_at DATETIME DEFAULT NULL')
    now = datetime.now().isoformat()
    cur.execute('UPDATE sessions SET last_active_at = ? WHERE last_active_at IS NULL', (now,))
    print(f'ADDED: last_active_at, backfilled {cur.rowcount} rows')
else:
    print('SKIP: last_active_at')

conn.commit()

cur.execute('PRAGMA table_info(sessions)')
print('\nFinal sessions columns:')
for c in cur.fetchall():
    print(f'  {c[1]} ({c[2]})')

conn.close()
print('\nMigration complete.')
