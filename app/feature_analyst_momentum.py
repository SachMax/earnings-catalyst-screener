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
    c.execute("ALTER TABLE features ADD COLUMN recommendationMean REAL")
except sqlite3.OperationalError:
    pass

today = date.today()
df_ed = pd.read_sql("""SELECT * FROM earnings_calendar WHERE earnings_date > ?""",
                    conn,
                    parse_dates= 'earnings_date',
                    params=(today.strftime("%Y-%m-%d"),))

for index,row in df_ed.iterrows():
    ticker = row['ticker']
    ed_clean = row['earnings_date'].date()
    try:
        stock = yf.Ticker(ticker)
        momentum = stock.info.get('recommendationMean', None)
    except Exception as e:
        print(f"{ticker}: yfinance error – {e}")
        continue
    time.sleep(0.3)
    if momentum is None:
        print(f"{ticker} -- not enough data")
        continue
    momentum = round(float(momentum), 2)
    print(f"\n{ticker}: momentum = {momentum}")
    c.execute("UPDATE features SET recommendationMean = ? WHERE ticker = ? AND earnings_date = ?",
          (float(momentum), ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()
    


