import yfinance as yf
from datetime import date, timedelta
import time
import pandas as pd
import sqlite3

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

try:
    c.execute("ALTER TABLE features ADD COLUMN short_interest REAL;")
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
        si = stock.info.get('shortPercentOfFloat', None)
    except Exception as e:
        print(f"{ticker}: yfinance error – {e}")
        continue
    time.sleep(0.3)
    if si is None:
        print(f"{ticker} -- not enough data")
        continue
    si = round(float(si) * 100, 2)
    print(f"\n{ticker}: short interest = {si}")
    c.execute("UPDATE features SET short_interest = ? WHERE ticker = ? AND earnings_date = ?",
          (float(si), ticker, ed_clean.strftime("%Y-%m-%d")))
    if c.rowcount == 0:
        c.execute("INSERT OR REPLACE INTO features (ticker, earnings_date, runup, rsi, short_interest) VALUES (?, ?, NULL, NULL, ?)",
                (ticker, ed_clean.strftime("%Y-%m-%d"), float(si)))
    conn.commit()
conn.close()
    


