# backfill_guidance_bert.py
import sqlite3
import pandas as pd
import time
from datetime import date
from features_library import load_earnings_dates, compute_guidance_bert  # your new function

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

# Add column if not exists
try:
    c.execute("ALTER TABLE ml_dataset ADD COLUMN guidance_bert_raise_prob REAL")
except sqlite3.OperationalError:
    pass
conn.commit()

# Select rows that have features and still need the new column filled
df = pd.read_sql("""
    SELECT ticker, earnings_date FROM ml_dataset
    WHERE runup IS NOT NULL
      AND guidance_bert_raise_prob IS NULL
    ORDER BY earnings_date DESC
    LIMIT 20000   -- adjust batch size as you like
""", conn, parse_dates=['earnings_date'])

print(f"Processing {len(df)} rows...")

for idx, row in df.iterrows():
    ticker = row['ticker']
    ed = row['earnings_date'].date()
    prob = compute_guidance_bert(ticker, ed)
    print(f"{ticker} ({ed}): {prob}")
    if prob is not None:
        c.execute("""
            UPDATE ml_dataset SET guidance_bert_raise_prob = ?
            WHERE ticker = ? AND earnings_date = ?
        """, (prob, ticker, ed.strftime('%Y-%m-%d')))
        conn.commit()
    time.sleep(0.05)   # be polite to EDGAR

conn.close()
print("Backfill complete.")