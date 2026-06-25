# fix_sector_columns.py
import sqlite3
import pandas as pd
from features_library import current_earnings_quality

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

df = pd.read_sql("""
    SELECT ticker, earnings_date
    FROM ml_dataset
    WHERE quality_curr IS NOT NULL
      AND (eps_beat_curr IS NULL OR eps_surprise_pct IS NULL)
    ORDER BY earnings_date
""", conn, parse_dates=['earnings_date'])

print(f"Rows to update: {len(df)}")

ticker_cache = {}
for i, (_, row) in enumerate(df.iterrows(), 1):
    ticker = row['ticker']
    ed = row['earnings_date'].date()

    quality_curr = current_earnings_quality(ticker, ed)
    if quality_curr is None:
        print(f"{ticker} ({ed}): no data")
        continue
    c.execute("""
        UPDATE ml_dataset SET
            eps_beat_curr = ?,
            eps_surprise_pct = ?
        WHERE ticker = ? AND earnings_date = ?
    """, (
        quality_curr['eps_beat'],
        quality_curr['eps_surprise_pct'],
        ticker, ed.strftime('%Y-%m-%d')
    ))
    print(f"{ticker} ({ed}): {quality_curr['eps_surprise_pct']}")
    if i % 1000 == 0:
        print(f"  {i} rows processed...")
    conn.commit()

conn.close()
print("columns backfilled.")