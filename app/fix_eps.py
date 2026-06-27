# fix_eps.py
import sqlite3
import pandas as pd
from features_library import current_earnings_quality

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

df = pd.read_sql("""
    SELECT ticker, earnings_date
    FROM ml_dataset
    WHERE quality_curr IS NOT NULL
      AND earnings_date >= '2026-05-15'
    ORDER BY earnings_date
""", conn, parse_dates=['earnings_date'])

print(f"Rows to update: {len(df)}")

for i, (_, row) in enumerate(df.iterrows(), 1):
    ticker = row['ticker']
    ed = row['earnings_date'].date()

    result = current_earnings_quality(ticker, ed)

    if result is None:
        eps_beat_val = -1
        eps_surp_val = -9999.0
    else:
        eps_beat_val = result.get('eps_beat', -1)
        eps_surp_val = result.get('eps_surprise_pct', -9999.0)
        if eps_beat_val is None:
            eps_beat_val = -1
        if eps_surp_val is None:
            eps_surp_val = -9999.0

    c.execute("""
        UPDATE ml_dataset SET
            eps_beat_curr = ?,
            eps_surprise_pct = ?
        WHERE ticker = ? AND earnings_date = ?
    """, (
        eps_beat_val,
        eps_surp_val,
        ticker, ed.strftime('%Y-%m-%d')
    ))
    print(f"{ticker} ({ed}): {eps_surp_val}")
    if i % 1000 == 0:
        print(f"  {i} rows processed...")
    conn.commit()

conn.close()
print("EPS columns backfilled.")