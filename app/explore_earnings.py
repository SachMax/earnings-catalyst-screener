import yfinance as yf
from datetime import date, timedelta
import time
import pandas as pd
import sqlite3

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS price_history (
          TICKER TEXT, DATE TEXT, CLOSE REAL, VOLUME INTEGER, PRIMARY KEY(TICKER, DATE))
""")

c.execute("""
CREATE TABLE IF NOT EXISTS earnings_calendar (
          ticker TEXT, earnings_date TEXT, eps_estimate REAL, revenue_estimate REAL, PRIMARY KEY(ticker, earnings_date))
""")

today = date.today()
cutoff = today + timedelta(days=60)

tickers = ["NVDA", "WMT", "PEP", "TSM", "GS", "AVGO", "CRWD"]
inserted_rows = 0
for i in tickers:
    print(f"\nChecking {i}...")
    time.sleep(0.3)

    try:
        stock = yf.Ticker(i)
        cal = stock.calendar

        if not cal or 'Earnings Date' not in cal:
            print(f"{i}: no calendar data")
            continue

        earning_date = cal['Earnings Date']

        if not earning_date:
            print(f"no upcoming earning")
            continue

        next_earnings = None
        for ed in earning_date:
            ed_clean = pd.Timestamp(ed).date()
            if today < ed_clean <= cutoff:
                next_earnings = ed_clean
                break
                
        if next_earnings:
            print(f"{i}: next earnings on {next_earnings} (within window)")
            print("pulling data...")
            time.sleep(0.5)
            hist = stock.history(period="5y")
            if hist.empty: 
                print(f"{i} - no history data, skipping")
                continue
            for index, row in hist.iterrows():
                py_date = index.strftime("%Y-%m-%d")
                py_close = float(row['Close'])
                py_volume = int(row['Volume'])
                c.execute("INSERT OR REPLACE INTO price_history VALUES (?, ?, ?, ?)", (i, py_date, py_close, py_volume))
                inserted_rows += 1    
            conn.commit()

            eps_est = None
            rev_est = None
            if 'Earnings Average' in cal:
                eps_est = cal['Earnings Average']
            if 'Revenue Average' in cal:
                rev_est = cal['Revenue Average']
            c.execute("INSERT OR REPLACE INTO earnings_calendar VALUES (?, ?, ?, ?)", (i, next_earnings, eps_est, rev_est))
            conn.commit()
        else:
            print(f"{i}: no upcoming earnings within 60 days")
            
    except Exception as e:
        print(f"{i}: error - {e}")

print(f"Rows inserted: {inserted_rows}")
conn.commit()
conn.close()