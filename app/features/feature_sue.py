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
    c.execute("ALTER TABLE features ADD COLUMN sue REAL")
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
        time.sleep(0.5)
        if earnings is None or earnings.empty:
            print(f"{ticker}: no earnings history data, skipping...")
            continue
        earnings = earnings.sort_index(ascending=False)
        sue = earnings['Surprise(%)'].iloc[0]
        if pd.isna(sue): 
            for _,irow in earnings.iterrows():
                reported = irow['Reported EPS']
                estimated = irow['EPS Estimate']
                if not pd.isna(reported) and not pd.isna(estimated):
                    surp = irow['Surprise(%)']
                    if not pd.isna(surp):
                        sue = surp
                    else:
                        if estimated != 0:
                            sue = round((reported - estimated) / abs(estimated) * 100, 2)
                    break
            
    except Exception as e:
        print(f"{ticker}: yfinance error – {e}")
        continue
    if pd.isna(sue):
        print(f"{ticker}: no SUE data, skipping")
        continue
    print(f"\n{ticker}: SUE = {float(sue)}")
    c.execute("UPDATE features SET sue = ? WHERE ticker = ? AND earnings_date = ?",
          (float(sue), ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()
    


