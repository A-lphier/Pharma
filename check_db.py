import sqlite3
conn = sqlite3.connect('/home/agent/.openclaw/workspace/fattura-mvp-modern/integratori.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()
print("Tables:", tables)
for t in tables:
    tname = t[0]
    cur.execute(f"SELECT COUNT(*) FROM {tname}")
    print(f"  {tname}: {cur.fetchone()[0]} rows")
if ('products',) in tables:
    cur.execute("SELECT COUNT(*) FROM products WHERE fonte='farmaciauno'")
    print("farmaciauno count:", cur.fetchone()[0])
    # Show existing columns
    cur.execute("PRAGMA table_info(products)")
    print("Columns:", [r[1] for r in cur.fetchall()])
conn.close()
