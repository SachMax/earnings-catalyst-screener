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
    c.execute("ALTER TABLE features ADD COLUMN eps_beat INTEGER")
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
        earnings = stock.earnings_dates
        time.sleep(0.3)
        if earnings is None or earnings.empty:
            print(f"{ticker}: no earnings history data, skipping...")
            continue
        earnings = earnings.sort_index(ascending=False)
        eps_beat = None
        for _,irow in earnings.iterrows():
            eps = irow.get('Surprise(%)')
            if not pd.isna(eps):
                eps_beat = 1 if eps > 0 else 0
                break
        if eps_beat is None:
            print(f"{ticker}: error - data not found")
            continue
        print(f"{ticker}: EPS beat = {eps_beat} | surprise = {eps}%")

    except Exception as e:
        print(f"{ticker}: yfinance error – {e}")
        continue
    c.execute("UPDATE features SET eps_beat = ? WHERE ticker = ? AND earnings_date = ?",
          (eps_beat, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()
    


