import yfinance as yf
from datetime import date, timedelta
import time
import pandas as pd
import sqlite3

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

# Create earnings_calendar table if not exists
c.execute("""
    CREATE TABLE IF NOT EXISTS earnings_calendar (
        ticker TEXT,
        earnings_date TEXT,
        eps_estimate REAL,
        revenue_estimate REAL,
        PRIMARY KEY (ticker, earnings_date)
    )
""")

c.execute("""
    DELETE FROM earnings_calendar
    WHERE earnings_date < date('now')
       OR earnings_date > date('now', '+7 days')
""")
conn.commit()

today = date.today()
cutoff_days = 7         # ← change this to whatever window you want
cutoff = today + timedelta(days=cutoff_days)

# Read the full US stock list
tickers_df = pd.read_csv('data/us_stocks.csv')
tickers = tickers_df['Symbol'].tolist()
print(f"Total tickers to check: {len(tickers)}")

inserted_events = 0
skipped_no_data = 0
skipped_no_upcoming = 0
errors = 0

for i, ticker in enumerate(tickers):
    if i % 100 == 0:
        print(f"Progress: {i}/{len(tickers)}")

    # Add a tiny delay to avoid rate limits
    time.sleep(0.1)

    try:
        stock = yf.Ticker(ticker)
        cal = stock.calendar

        if not cal or 'Earnings Date' not in cal:
            skipped_no_data += 1
            continue

        earnings_dates = cal['Earnings Date']
        if earnings_dates is None or len(earnings_dates) == 0:
            skipped_no_upcoming += 1
            continue

        next_earnings = None
        for ed in earnings_dates:
            ed_clean = pd.Timestamp(ed).date()
            if today < ed_clean <= cutoff:
                next_earnings = ed_clean
                break

        if next_earnings is None:
            skipped_no_upcoming += 1
            continue

        # Extract estimates
        eps_est = cal.get('Earnings Average', None)
        rev_est = cal.get('Revenue Average', None)

        c.execute(
            "INSERT OR REPLACE INTO earnings_calendar (ticker, earnings_date, eps_estimate, revenue_estimate) VALUES (?, ?, ?, ?)",
            (ticker, next_earnings.strftime('%Y-%m-%d'), eps_est, rev_est)
        )
        inserted_events += 1

    except Exception as e:
        errors += 1
        # Optionally log the error for later inspection
        # print(f"{ticker}: {e}")
        continue

conn.commit()
conn.close()

print(f"\nDone.")
print(f"Inserted: {inserted_events}")
print(f"Skipped (no data): {skipped_no_data}")
print(f"Skipped (no upcoming earnings): {skipped_no_upcoming}")
print(f"Errors: {errors}")
