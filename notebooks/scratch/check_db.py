import sqlite3

con = sqlite3.connect("data/earnings_calls.db")
cur = con.cursor()
tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tables in DB:", tables)
for t in tables:
    tname = t[0]
    cols = cur.execute(f"PRAGMA table_info({tname})").fetchall()
    print(f"Table {tname}:", [c[1] for c in cols])
    rows = cur.execute(f"SELECT * FROM {tname} LIMIT 10").fetchall()
    print(f"Rows in {tname}: {len(rows)}")
    for r in rows:
        print(r)
