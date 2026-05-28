import sqlite3
import pandas as pd
from datetime import date, timedelta
import numpy as np
import time
import yfinance as yf

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

try:
    c.execute("ALTER TABLE features ADD COLUMN post_earnings_drift REAL;")
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
    try:
        ticker = row['ticker']
        ed_clean = row['earnings_date'].date()
        df = pd.read_sql(f"SELECT * FROM price_history WHERE ticker='{ticker}' ORDER BY date", conn, parse_dates='date', index_col='date')
        if df.empty:
            print(f"{ticker}: no price data, skipping")
            continue
        for attempt in range(3):
            try:
                stock = yf.Ticker(ticker)
                earnings_hist = stock.earnings_dates
                break
            except Exception:
                time.sleep(2)
        else:
            print(f"{ticker}: yfinance timed out after retries")
            continue
        if earnings_hist is None or earnings_hist.empty:
            print(f"{ticker} - not earnings history data")
            continue
        past_earnings = earnings_hist[earnings_hist.index.tz_localize(None) <= pd.Timestamp(today)]
        if len(past_earnings) < 2:
            print(f"{ticker}: not enough data")
            continue
        
        recent = past_earnings.sort_index().tail(4)
        drift_values = []
        for _,irow in recent.iterrows():
            earnings_date = irow.name.date()
            idx = df.index.get_indexer([earnings_date], method="ffill")[0]
            if idx < 0 or idx + 10 >= len(df):
                print(f"{ticker} - not enough data")
                continue
            close_start = df['close_price'].iloc[idx]
            idx10 = idx + 10
            close_end = df['close_price'].iloc[idx10]

            if pd.isna(close_start) or pd.isna(close_end) or close_start == 0:
                print(f"{ticker}: invalid price data for {earnings_date}, skipping event")
                continue

            value = ((close_end - close_start)/close_start)*100
            drift_values.append(value)
        if len(drift_values) < 2:
            print(f"{ticker}: not enough data")
            continue
        avg_drift = round(float(np.mean(drift_values)), 2)
    except Exception as e:
        print(f"{ticker}: error -> {e}")
        continue
    print(f"{ticker}: avg_drift -> {avg_drift}%")
    c.execute("UPDATE features SET post_earnings_drift = ? WHERE ticker = ? AND earnings_date = ?",
          (avg_drift, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()