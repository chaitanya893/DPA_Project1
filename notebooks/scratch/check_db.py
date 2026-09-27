import sqlite3
import pandas as pd

conn = sqlite3.connect('data/earnings_calls.db')
tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)
print("Tables:", tables['name'].tolist())

for tbl in tables['name'].tolist():
    df = pd.read_sql(f"SELECT * FROM {tbl} LIMIT 5;", conn)
    print(f"\n--- Table: {tbl} (rows: {len(pd.read_sql(f'SELECT count(*) as c FROM {tbl}', conn))}) ---")
    print(df.columns.tolist())
    if 'ticker' in df.columns or 'url' in df.columns:
        print(df.head(2))
