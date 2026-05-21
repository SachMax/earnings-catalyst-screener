import sqlite3
import pandas as pd
from datetime import date, timedelta
import yfinance as yf
import numpy as np
import time

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

try:
    c.execute("ALTER TABLE features ADD COLUMN past_earnings_action TEXT;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN surge_hold_count INTEGER;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN fade_count INTEGER;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN drop_count INTEGER;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN pct_surge_hold REAL;")
except sqlite3.OperationalError:
    pass   # column already exists

today = date.today()
df_ed = pd.read_sql(
    "SELECT * FROM earnings_calendar WHERE earnings_date > ?",
    conn,
    params=(today.strftime("%Y-%m-%d"),),
    parse_dates='earnings_date'
)

def get_close_prev(df, target):
    try:
        return df.loc[target, 'close_price']
    except KeyError:
        idx = df.index.get_indexer([target], method='ffill')[0]
        return df.iloc[idx]['close_price']

for index,row in df_ed.iterrows(): 
    try:
        ticker = row['ticker']
        ed_clean = row['earnings_date'].date()
        df = pd.read_sql(f"SELECT * FROM price_history WHERE ticker='{ticker}' ORDER BY date", conn, parse_dates='date', index_col='date')

        if df.empty: 
            print(f"no data in {ticker}, skipping...")
            continue

        try:
            stock = yf.Ticker(ticker)
            earnings_hist = stock.earnings_dates
            time.sleep(1.8)
            if earnings_hist.empty or earnings_hist is None:
                print(f"{ticker}: no earnings history data, skipping")
                continue
            if not isinstance(earnings_hist.index, pd.DatetimeIndex):
                print(f"{ticker}: unexpected earnings data format, skipping")
                continue
            earnings_hist.index = earnings_hist.index.tz_localize(None)
            past_earnings = earnings_hist[earnings_hist.index <= pd.Timestamp(today)]
            
            if len(past_earnings) < 2:
                print(f"{ticker}: not enough past earnings, skipping")
                continue

            recent = past_earnings.sort_index().tail(4)
            historical_action = []
            for _,erow in recent.iterrows():
                hist_date = erow.name.date()
                d0 = hist_date
                d1 = hist_date + timedelta(days=1)
                d5 = hist_date + timedelta(days=5)
                
                try:
                    close0 = get_close_prev(df, d0)
                    
                    idx1 = df.index.get_indexer([d1], method="bfill")[0]
                    idx5 = idx1 + 5
                    if idx1 < 0 or idx1 >= len(df):
                        continue
                    if idx5 >= len(df):
                        continue
                    close1 = df['close_price'].iloc[idx1]
                    close5 = df['close_price'].iloc[idx5]
                    if pd.isna(close0) or pd.isna(close1) or pd.isna(close5) or close0 == 0:
                        continue
                    return01 = (close1 - close0) / close0 * 100

                    if return01 > 0:
                        initial_gain = close1 - close0
                        loss_from_peak = max(0, close1 - close5)
                        gave_back = loss_from_peak > 0.5 * initial_gain
                        label = 'Fade' if gave_back else 'Surge & Hold'
                    else:
                        label = 'Drop'

                    historical_action.append(label)
                except Exception as t:
                    print(f"{ticker}: error - {t}")
                    continue
        except Exception as o:
            print(f"{ticker}: error -> {o}")
            continue
        if len(historical_action) < 2:
            print(f"{ticker}: not enough data, skipping...")
            continue
        total = len(historical_action)
        surge_count = None
        fade_count = None
        drop_count = None
        pct_surge = None
        if total > 0:
            surge_count = historical_action.count('Surge & Hold')
            fade_count = historical_action.count('Fade')
            drop_count = historical_action.count('Drop')
            pct_surge = round(surge_count/total, 2)
        else:
            pass
        most_common = max(historical_action, key=historical_action.count)
        print(f"{ticker}: most common past earnings reaction = {most_common} from {historical_action}")
    except Exception as e:
        print(f"{ticker}: error -> {e}")
        continue
    if surge_count is not None:
        c.execute("UPDATE features SET surge_hold_count = ? WHERE ticker = ? AND earnings_date = ?",
        (surge_count, ticker, ed_clean.strftime("%Y-%m-%d")))
    if fade_count is not None:
        c.execute("UPDATE features SET fade_count = ? WHERE ticker = ? AND earnings_date = ?",
        (fade_count, ticker, ed_clean.strftime("%Y-%m-%d")))
    if drop_count is not None:
        c.execute("UPDATE features SET drop_count = ? WHERE ticker = ? AND earnings_date = ?",
        (drop_count, ticker, ed_clean.strftime("%Y-%m-%d")))
    if most_common is not None:
        c.execute("UPDATE features SET past_earnings_action = ? WHERE ticker = ? AND earnings_date = ?",
            (most_common, ticker, ed_clean.strftime("%Y-%m-%d")))
    if pct_surge is not None:
        c.execute("UPDATE features SET pct_surge_hold = ? WHERE ticker = ? AND earnings_date = ?",
            (pct_surge, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()