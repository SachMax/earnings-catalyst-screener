import sqlite3
import pandas as pd
from datetime import date, timedelta
import yfinance as yf

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

df = pd.read_sql("SELECT * FROM price_history WHERE ticker='WMT' ORDER BY date", conn, parse_dates='date', index_col='date')

wmt = yf.Ticker("WMT")
earnings_calendar = wmt.calendar
earnings_date = earnings_calendar['Earnings Date']
ed_clean = earnings_date[0]

date_14d_before = ed_clean - timedelta(days=14)
date_2d_before = ed_clean - timedelta(days=2)

# 14 days before
try:
    close_14d_before = df.loc[date_14d_before, 'close_price']
    used_14d = date_14d_before
except KeyError:
    idx_14d = df.index.get_indexer([date_14d_before], method='ffill')[0]
    used_14d = df.index[idx_14d].date()
    close_14d_before = df.iloc[idx_14d]['close_price']
    print(f"Used nearest trading day {used_14d} instead of {date_14d_before}")

# 2 days before
try:
    close_2d_before = df.loc[date_2d_before, 'close_price']
    used_2d = date_2d_before
except KeyError:
    idx_2d = df.index.get_indexer([date_2d_before], method='ffill')[0]
    used_2d = df.index[idx_2d].date()
    close_2d_before = df.iloc[idx_2d]['close_price']
    print(f"Used nearest trading day {used_2d} instead of {date_2d_before}")

print(f"Close price on {used_14d}: {close_14d_before}")
print(f"Close price on {used_2d}: {close_2d_before}")

runup = (close_2d_before - close_14d_before) / close_14d_before
print(f"\nPre‑earnings run‑up for WMT: {runup:.2%}")