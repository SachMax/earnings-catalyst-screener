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
try:
    c.execute("ALTER TABLE features ADD COLUMN analyst_upgrades INTEGER")
except sqlite3.OperationalError:
    pass
try:
    c.execute("ALTER TABLE features ADD COLUMN analyst_downgrades INTEGER")
except sqlite3.OperationalError:
    pass
try:
    c.execute("ALTER TABLE features ADD COLUMN net_analyst_momentum INTEGER")
except sqlite3.OperationalError:
    pass

today = date.today()
df_ed = pd.read_sql("""SELECT * FROM earnings_calendar WHERE earnings_date > ?""",
                    conn,
                    parse_dates= 'earnings_date',
                    params=(today.strftime("%Y-%m-%d"),))

def rating_tier(grade):
    grade_lower = str(grade).lower()
    if grade_lower in ['buy','overweight','outperform']:
        return 2   # bullish
    elif grade_lower in ['hold','neutral','market perform','sector perform']:
        return 1   # neutral
    elif grade_lower in ['sell','underperform','underweight']:
        return 0   # bearish
    return 1  # unknown -> treat as neutral

for index,row in df_ed.iterrows():
    ticker = row['ticker']
    ed_clean = row['earnings_date'].date()
    try:
        stock = yf.Ticker(ticker)
        momentum = stock.info.get('recommendationMean', None)
    except Exception as e:
        print(f"{ticker}: yfinance error – {e}")
        continue
    try:
        downgrades = stock.upgrades_downgrades
        last2weeks = pd.Timestamp(today) - timedelta(days=14)
        recent = downgrades[downgrades.index >= last2weeks]
        downgrade_count = 0
        upgrade_count = 0
        for _, rrow in recent.iterrows():
            grade_from = rating_tier(rrow.get('FromGrade', ''))
            grade_to = rating_tier(rrow.get('ToGrade', ''))
            if grade_to < grade_from:
                downgrade_count += 1
            if grade_to > grade_from:
                upgrade_count += 1
        net_analyst_momentum = upgrade_count - downgrade_count
    except Exception as o:
        print(f"{ticker}: yfinance error – {o}")
        continue

    time.sleep(0.3)
    if momentum is None:
        print(f"{ticker} -- not enough data")
        continue
    momentum = round(float(momentum), 2)
    print(f"\n{ticker}: momentum = {momentum}")
    c.execute("UPDATE features SET recommendationMean = ? WHERE ticker = ? AND earnings_date = ?",
          (float(momentum), ticker, ed_clean.strftime("%Y-%m-%d")))
    c.execute("UPDATE features SET analyst_upgrades = ? WHERE ticker = ? AND earnings_date = ?",
          (upgrade_count, ticker, ed_clean.strftime("%Y-%m-%d")))
    c.execute("UPDATE features SET analyst_downgrades = ? WHERE ticker = ? AND earnings_date = ?",
          (downgrade_count, ticker, ed_clean.strftime("%Y-%m-%d")))
    c.execute("UPDATE features SET net_analyst_momentum = ? WHERE ticker = ? AND earnings_date = ?",
          (net_analyst_momentum, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()
    


