# fix_sector_columns.py
import sqlite3
import pandas as pd
import time
from features_library import compute_sector_relative_strength, load_price_history

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

df = pd.read_sql("""
    SELECT ticker, earnings_date
    FROM ml_dataset
    WHERE quality_curr IS NOT NULL
      AND (stock_vs_spy_20d IS NULL OR stock_vs_sector_20d IS NULL OR sector_relative_strength IS NULL)
    ORDER BY earnings_date
""", conn, parse_dates=['earnings_date'])

print(f"Rows to update: {len(df)}")

ticker_cache = {}
for i, (_, row) in enumerate(df.iterrows(), 1):
    ticker = row['ticker']
    ed = row['earnings_date'].date()
    if ticker not in ticker_cache:
        ticker_cache[ticker] = load_price_history(ticker)
    df_price = ticker_cache[ticker]
    if df_price.empty:
        continue

    rel_str = compute_sector_relative_strength(ticker, ed, df_price)
    time.sleep(1.5)
    if rel_str is None:
        continue
    c.execute("""
        UPDATE ml_dataset SET
            sector_relative_strength = ?,
            stock_vs_spy_20d = ?,
            stock_vs_sector_20d = ?
        WHERE ticker = ? AND earnings_date = ?
    """, (
        rel_str['sector_spy_return_ratio'],
        rel_str['stock_vs_spy_20d'],
        rel_str['stock_vs_sector_20d'],
        ticker, ed.strftime('%Y-%m-%d')
    ))
    print(f"{ticker} ({ed}): {rel_str['sector_spy_return_ratio']}")
    if i % 1000 == 0:
        print(f"  {i} rows processed...")
    conn.commit()

conn.close()
print("Sector columns backfilled.")