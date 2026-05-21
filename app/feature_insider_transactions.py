import yfinance as yf
from datetime import date, timedelta
import time
import pandas as pd
import sqlite3
import edgar

edgar.set_identity("sachiomaximilliano166@gmail.com")

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

try:
    c.execute("ALTER TABLE features ADD COLUMN insider_transactions INTEGER;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN insider_net_value REAL;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN insider_buy_count INTEGER;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN insider_sell_count INTEGER;")
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
        company = edgar.Company(ticker)
        form4s = company.get_filings(form="4").head(20)
        count = 0
        total_net = 0
        total_buy_value = 0
        total_sell_value = 0
        buy_count = 0
        sell_count = 0
        for f in form4s:
            if f is not None:
                ownership = f.obj()
                summary = ownership.get_ownership_summary()
                if summary is None:  
                    print(f"{ticker} - no summary provided")
                    continue
                if summary.primary_activity in ('Purchase', 'Sale'):
                    total_net = total_net + summary.net_change
                    count += 1
                if summary.primary_activity in ('Purchase'):
                    total_buy_value += summary.net_value
                    buy_count += 1
                if summary.primary_activity in ('Sell'):
                    total_sell_value += abs(summary.net_value)
                    sell_count += 1
                insider_net_value = round(total_buy_value - total_sell_value, 2)
            else:
                continue
        if count == 0:
            print(f"{ticker}: no insider transactions, skipping...")
            continue
        insider_flag = 0
        if total_net > 0:
            insider_flag = 1 
        else:
            insider_flag = 0
        
        print(f"{ticker}: net insider change = {total_net} shares ({count} filings), flag = {insider_flag}")

    except Exception as e:
        print(f"{ticker}: yfinance error – {e}")
        continue
    c.execute("UPDATE features SET insider_transactions = ? WHERE ticker = ? AND earnings_date = ?",
          (insider_flag, ticker, ed_clean.strftime("%Y-%m-%d")))
    c.execute("UPDATE features SET insider_net_value = ? WHERE ticker = ? AND earnings_date = ?",
          (insider_net_value, ticker, ed_clean.strftime("%Y-%m-%d")))
    c.execute("UPDATE features SET insider_buy_count = ? WHERE ticker = ? AND earnings_date = ?",
          (buy_count, ticker, ed_clean.strftime("%Y-%m-%d")))
    c.execute("UPDATE features SET insider_sell_count = ? WHERE ticker = ? AND earnings_date = ?",
          (sell_count, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()
    


