import yfinance as yf
from datetime import date, timedelta
import time
import pandas as pd
import sqlite3

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

try:
    c.execute("ALTER TABLE features ADD COLUMN peg_ratio REAL;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN pct_from_52w_low REAL;")
except sqlite3.OperationalError:
    pass   # column already exists

today = date.today()
df_ed = pd.read_sql(
    "SELECT * FROM earnings_calendar WHERE earnings_date > ?",
    conn,
    params=(today.strftime("%Y-%m-%d"),),
    parse_dates='earnings_date'
)

for index,row in df_ed.iterrows():
    ticker = row['ticker']
    ed_clean = row['earnings_date'].date()
    try:
        stock = yf.Ticker(ticker)
        pegRatio = stock.info.get('pegRatio', None)
        if pegRatio is not None:
            pegRatio = round(pegRatio, 2)
        high52weeks = stock.info.get('fiftyTwoWeekHigh', None)
        low52weeks = stock.info.get('fiftyTwoWeekLow', None)
        current_price = stock.info.get('currentPrice', None) or stock.info.get('regularMarketPrice', None)

        if current_price and high52weeks and low52weeks and (high52weeks != low52weeks):
            pct = ((current_price - low52weeks)/(high52weeks - low52weeks)) * 100
            pct = round(pct, 2)
        else:
            pct = None

    except Exception as e:
        print(f"{ticker}: yfinance error – {e}")
        continue
    time.sleep(0.3)
    if pct is not None:
        c.execute("UPDATE features SET pct_from_52w_low = ? WHERE ticker = ? AND earnings_date = ?",
                  (pct, ticker, ed_clean.strftime("%Y-%m-%d")))
        print(f"{ticker}: 52‑week position = {pct}%")
    if pegRatio is not None:
        c.execute("UPDATE features SET peg_ratio = ? WHERE ticker = ? AND earnings_date = ?",
                  (pegRatio, ticker, ed_clean.strftime("%Y-%m-%d")))
        print(f"{ticker}: PEG ratio = {pegRatio}")
    conn.commit()
conn.close()
    


