import sqlite3
import pandas as pd
from datetime import date, timedelta
import time
import requests
from config import FMP_KEY   # Replace with `FMP_KEY = "abcdefghijklmn"` for now

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

# Placeholder rows for all upcoming earnings
c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

# Add the revenue_beat column
try:
    c.execute("ALTER TABLE features ADD COLUMN revenue_beat INTEGER")
except sqlite3.OperationalError:
    pass

today = date.today()
df_ed = pd.read_sql(
    "SELECT * FROM earnings_calendar WHERE earnings_date > ?",
    conn,
    params=(today.strftime("%Y-%m-%d"),),
    parse_dates='earnings_date'
)

# FMP base URL for earnings calendar
FMP_BASE = "https://financialmodelingprep.com/stable/earnings-calendar"

for index, row in df_ed.iterrows():
    ticker = row['ticker']
    ed_clean = row['earnings_date'].date()

    try:
        # Build API parameters – look at a 120‑day window around earnings
        start_date = ed_clean - timedelta(days=60)
        end_date = ed_clean + timedelta(days=60)
        params = {
            "symbol": ticker,
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d"),
            "apikey": FMP_KEY
        }

        response = requests.get(FMP_BASE, params=params)
        if response.status_code != 200:
            print(f"{ticker}: FMP error {response.status_code}")
            continue

        data = response.json()
        if not data or len(data) == 0:
            print(f"{ticker}: no earnings data in FMP")
            continue

        # Find the quarter that matches our earnings_date most closely
        best = None
        for entry in data:
            entry_date = entry.get('date')
            if entry_date is None:
                continue
            if entry_date == ed_clean.strftime("%Y-%m-%d"):
                best = entry
                break
        if best is None:
            best = data[0]   # fallback: take first entry

        rev_actual = best.get('revenueActual')
        rev_estimate = best.get('revenueEstimated')

        if rev_actual is None or rev_estimate is None:
            print(f"{ticker}: revenue data missing in FMP")
            continue

        revenue_beat = 1 if rev_actual > rev_estimate else 0
        print(f"{ticker}: revenue beat = {revenue_beat} (actual={rev_actual}, est={rev_estimate})")

        c.execute("UPDATE features SET revenue_beat = ? WHERE ticker = ? AND earnings_date = ?",
                  (revenue_beat, ticker, ed_clean.strftime("%Y-%m-%d")))
        conn.commit()

    except Exception as e:
        print(f"{ticker}: error – {e}")
        continue

    time.sleep(0.3)   # be gentle to the API

conn.close()
print("Done.")