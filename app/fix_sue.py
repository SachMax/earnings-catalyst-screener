# fix_sector_columns.py
import sqlite3
import pandas as pd
from features_library import compute_sue

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

df = pd.read_sql("""
    SELECT ticker, earnings_date
    FROM ml_dataset
    WHERE quality_curr IS NOT NULL
      AND sue IS NULL AND earnings_date >= '2020-01-01'
    ORDER BY earnings_date
""", conn, parse_dates=['earnings_date'])

print(f"Rows to update: {len(df)}")

ticker_cache = {}
for i, (_, row) in enumerate(df.iterrows(), 1):
    ticker = row['ticker']
    ed = row['earnings_date'].date()

    sue = compute_sue(ticker, ed)
    if sue is None:
        sue = -9999.0
    c.execute("""
        UPDATE ml_dataset SET
            sue = ?
        WHERE ticker = ? AND earnings_date = ?
    """, (
        sue,
        ticker, ed.strftime('%Y-%m-%d')
    ))
    print(f"{ticker} ({ed}): {sue}")
    if i % 1000 == 0:
        print(f"  {i} rows processed...")
    conn.commit()

conn.close()
print("columns backfilled.")