import sqlite3
import pandas as pd
from datetime import date, timedelta
import time
import yfinance as yf

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
        revenue_beat = None
        for _,irow in earnings.iterrows():
            reported = irow.get('Reported Revenue')
            estimated = irow.get('Revenue Estimate')
            if pd.notna(reported) and pd.notna(estimated):
                revenue_beat = 1 if reported > estimated else 0
                break
        if reported is None or estimated is None:
            print(f"{ticker}: error - data not found")
            continue
        surprise = round(((reported - estimated)/estimated)*100,2)
        print(f"{ticker}: Revenue beat = {revenue_beat} | surprise = {surprise}%")

    except Exception as e:
        print(f"{ticker}: yfinance error – {e}")
        continue

    c.execute("UPDATE features SET revenue_beat = ? WHERE ticker = ? AND earnings_date = ?",
                (revenue_beat, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()

conn.close()