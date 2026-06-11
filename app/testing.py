# fix_sector_relative_strength.py
import sqlite3
import pandas as pd
from datetime import date, timedelta
from features_library import *

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

# Select all rows that already have features but might have NULL or stale sector relative strength
df = pd.read_sql("""
    SELECT ticker, earnings_date
    FROM ml_dataset
    WHERE quality_curr IS NOT NULL
    ORDER BY earnings_date
""", conn, parse_dates=['earnings_date'])

print(f"Rows with existing features: {len(df)}")

ticker_cache = {}
for idx, row in df.iterrows():
    ticker = row['ticker']
    ed = row['earnings_date'].date()

    if ticker not in ticker_cache:
        try:
            df_price = load_price_history(ticker)
            ed_series = load_earnings_dates(ticker)
            ticker_cache[ticker] = (df_price, ed_series)
        except:
            ticker_cache[ticker] = (pd.DataFrame(), pd.Series())
    df_price, ed_series = ticker_cache[ticker]
    if df_price.empty:
        continue

    rel_str = compute_sector_relative_strength(ticker, ed, df_price)
    if rel_str is None:
        continue
    print(rel_str)
    print("\n") 
    c.execute("""
        UPDATE ml_dataset SET
            sector_relative_strength = ?,
            stock_vs_spy_20d = ?,
            stock_vs_sector_20d = ?
        WHERE ticker = ? AND earnings_date = ?
    """, (
        rel_str.get('sector_spy_return_ratio'),
        rel_str.get('stock_vs_spy_20d'),
        rel_str.get('stock_vs_sector_20d'),
        ticker,
        ed.strftime('%Y-%m-%d')
    ))
    conn.commit()

conn.close()
print("Sector relative strength columns updated in ml_dataset.")