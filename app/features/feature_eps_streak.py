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
    c.execute("ALTER TABLE features ADD COLUMN eps_streak INTEGER")
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
        earnings = earnings.dropna(subset=['Surprise(%)'])
        if earnings.empty:
            print(f"{ticker}: no earnings history data, skipping...")
            continue
        earnings = earnings.sort_index(ascending=False)
        eps_streak = 0
        for _,irow in earnings.iterrows():
            if irow['Surprise(%)'] > 0:
                eps_streak += 1
            else:
                break
    except Exception as e:
        print(f"{ticker}: yfinance error – {e}")
        continue
    print(f"\n{ticker}: EPS Beat Streak = {eps_streak}")
    c.execute("UPDATE features SET eps_streak = ? WHERE ticker = ? AND earnings_date = ?",
          (eps_streak, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()
    


