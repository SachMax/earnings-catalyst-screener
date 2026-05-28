import sqlite3
import pandas as pd
from datetime import date, timedelta, datetime
import requests
import yfinance as yf
import time
from config import FMP_KEY

FMP_API_KEY = FMP_KEY   # paste your key

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

# Placeholder rows
c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

try:
    c.execute("ALTER TABLE features ADD COLUMN revenue_beat INTEGER")
except sqlite3.OperationalError:
    pass

today = date.today()
df_ed = pd.read_sql("""
    SELECT * FROM earnings_calendar WHERE earnings_date > ?
""", conn, parse_dates='earnings_date', params=(today.strftime("%Y-%m-%d"),))

def find_best_estimate(data, earnings_date):
    """Find the closest quarterly estimate whose quarter-end is ≤ earnings_date."""
    best = None
    best_diff = float('inf')
    for est in data:
        try:
            est_date = datetime.strptime(est['date'], "%Y-%m-%d").date()
        except:
            continue
        if est_date <= earnings_date:
            diff = (earnings_date - est_date).days
            if diff < best_diff:
                best_diff = diff
                best = est
    return best.get('revenueAvg') if best else None

for index, row in df_ed.iterrows():
    ticker = row['ticker']
    ed_clean = row['earnings_date'].date()
    revenue_beat = None

    # 1. Get actual revenue from yfinance (latest quarter)
    try:
        stock = yf.Ticker(ticker)
        income = stock.quarterly_financials
        if income.empty or 'Total Revenue' not in income.index:
            print(f"{ticker}: no quarterly revenue data")
            continue
        # sort columns descending (most recent first)
        cols = sorted(income.columns, reverse=True)
        actual_revenue = income.loc['Total Revenue', cols[0]]
        if pd.isna(actual_revenue):
            print(f"{ticker}: actual revenue is NaN")
            continue
    except Exception as e:
        print(f"{ticker}: yfinance error – {e}")
        continue

    # 2. Get consensus estimate from FMP
    try:
        url = f"https://financialmodelingprep.com/stable/analyst-estimates?symbol={ticker}&period=quarter&apikey={FMP_API_KEY}"
        resp = requests.get(url)
        data = resp.json()
        if ticker == 'PEP':
            print(f"FMP raw response: {data}")
        time.sleep(0.2)
    except Exception as e:
        print(f"{ticker}: FMP request failed – {e}")
        continue

    consensus = find_best_estimate(data, ed_clean)
    if consensus is None:
        print(f"{ticker}: no consensus estimate found")
        continue

    # 3. Compute beat
    revenue_beat = 1 if actual_revenue > consensus else 0
    print(f"{ticker}: actual = {actual_revenue:,.0f}, consensus = {consensus:,.0f} → beat = {revenue_beat}")

    # 4. Store
    c.execute("UPDATE features SET revenue_beat = ? WHERE ticker = ? AND earnings_date = ?",
              (revenue_beat, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()

conn.close()