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
    c.execute("ALTER TABLE features ADD COLUMN gaap_profit INTEGER")
except sqlite3.OperationalError:
    pass
try:
    c.execute("ALTER TABLE features ADD COLUMN sbc_pct_revenue REAL")
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
        net_income = stock.info.get('netIncomeToCommon', None)
    except Exception as e:
        print(f"{ticker}: yfinance error – {e}")
        continue
    try:
        company = edgar.Company(ticker)
        facts = company.get_facts()
        sbc = facts.get_concept("StockBasedCompensation")   # latest annual
        revenue = facts.get_revenue()
        if sbc and revenue and revenue > 0:
            sbc_pct = round((sbc / revenue) * 100, 2)
        else:
            sbc_pct = None
    except Exception as o:
        print(f"{ticker}: yfinance error – {o}")
        sbc_pct = None
        continue
    time.sleep(0.3)
    if net_income is None:
        print(f"{ticker} -- no GAAP net income data, skipping")
        continue
    gaap_profit = 1 if net_income > 0 else 0
    print(f"{ticker}: GAAP profit = {gaap_profit} (net income = ${net_income:,})")
    c.execute("UPDATE features SET gaap_profit = ? WHERE ticker = ? AND earnings_date = ?",
          (gaap_profit, ticker, ed_clean.strftime("%Y-%m-%d")))
    c.execute("UPDATE features SET sbc_pct_revenue = ? WHERE ticker = ? AND earnings_date = ?",
          (sbc_pct, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()
    


