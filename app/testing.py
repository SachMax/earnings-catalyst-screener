import sqlite3
import pandas as pd
from datetime import date, timedelta
from features_library import compute_guidance_bert

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

today = date.today()
cutoff = today + timedelta(days=7)

df = pd.read_sql("""
    SELECT ticker, earnings_date
    FROM ml_dataset
    WHERE earnings_date BETWEEN date('now') AND ?
""", conn, params=(cutoff.strftime('%Y-%m-%d'),), parse_dates=['earnings_date'])

for _, row in df.iterrows():
    ticker = row['ticker']
    ed = row['earnings_date'].date()
    prob = compute_guidance_bert(ticker, ed)
    c.execute("""
        UPDATE ml_dataset SET guidance_bert_raise_prob = ?
        WHERE ticker = ? AND earnings_date = ?
    """, (prob, ticker, ed.strftime('%Y-%m-%d')))
    print(f"{ticker}: {prob}")
    conn.commit()

conn.close()