# backfill_fundamentals_to_features.py
import sqlite3
import pandas as pd
from datetime import date, timedelta
from features_library import current_earnings_quality, load_earnings_dates, compute_guidance_bert

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

# 1. Ensure the columns exist in features
for col in ['eps_beat', 'revenue_beat', 'gaap_clean', 'guidance_finbert_prob']:
    try:
        c.execute(f"ALTER TABLE features ADD COLUMN {col} REAL")
    except sqlite3.OperationalError:
        pass
conn.commit()

# 2. Get all upcoming events (next 7 days, same as your evaluation script)
today = date.today()
cutoff = today + timedelta(days=7)

df = pd.read_sql("""
    SELECT ticker, earnings_date
    FROM features
    WHERE earnings_date > date('now')
      AND earnings_date <= ?
    ORDER BY earnings_date
""", conn, params=(cutoff.strftime('%Y-%m-%d'),), parse_dates=['earnings_date'])

print(f"Backfilling fundamentals for {len(df)} upcoming events...")

for _, row in df.iterrows():
    ticker = row['ticker']
    ed = row['earnings_date'].date()

    # Get the most recent past earnings date (so we can compute prior‑quarter fundamentals)
    past_dates = load_earnings_dates(ticker)
    past_dates = past_dates[past_dates < pd.Timestamp(ed)]
    if past_dates.empty:
        continue
    prior_date = past_dates.sort_values(ascending=False).iloc[0].date()

    # Compute fundamentals using your existing, audited function
    curr = current_earnings_quality(ticker, prior_date)
    if curr is None:
        continue

    eps_beat = curr.get('eps_beat')
    revenue_beat = curr.get('revenue_beat')
    gaap_profit = curr.get('gaap_profit')     # This is what current_earnings_quality returns

    # Compute guidance probability from the most recent 8‑K before the upcoming date
    guidance_prob = compute_guidance_bert(ticker, ed)
    
    print("\n",ticker)
    print(f"eps beat: {eps_beat}, rev beat: {revenue_beat}, gaap profit: {gaap_profit}, guidance prob: {guidance_prob}")
    # Update the features table
    c.execute("""
        UPDATE features SET
            eps_beat = ?,
            revenue_beat = ?,
            gaap_clean = ?,
            guidance_finbert_prob = ?
        WHERE ticker = ? AND earnings_date = ?
    """, (
        eps_beat,
        revenue_beat,
        gaap_profit,           # features column is named 'gaap_clean'
        guidance_prob,
        ticker,
        ed.strftime('%Y-%m-%d')
    ))
    conn.commit()

conn.close()
print("Fundamental data backfilled to features table.")