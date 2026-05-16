import sqlite3
import pandas as pd
from datetime import date, timedelta


conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

try:
    c.execute("ALTER TABLE features ADD COLUMN rsi REAL;")
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
    df = pd.read_sql(f"SELECT * FROM price_history WHERE ticker='{ticker}' ORDER BY date", conn, parse_dates='date', index_col='date')

    if df.empty: 
        print(f"no data in {ticker}, skipping...")
        continue

    delta = df['close_price'].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    RS = avg_gain/avg_loss
    RSI = 100 - (100 / (1 + RS))
    latest_rsi = round(RSI.iloc[-1], 2)
    if pd.isna(latest_rsi):
        print(f"{ticker}: not enough data for RSI, skipping")
        continue

    c.execute("UPDATE features SET rsi = ? WHERE ticker = ? AND earnings_date = ?",
          (latest_rsi, ticker, ed_clean.strftime("%Y-%m-%d")))
    print(f"{ticker}: RSI = {latest_rsi:.2f}")
    if c.rowcount == 0:
        c.execute("INSERT OR REPLACE INTO features (ticker, earnings_date, runup, rsi) VALUES (?, ?, NULL, ?)",
                (ticker, ed_clean.strftime("%Y-%m-%d"), float(latest_rsi)))
    conn.commit()
conn.close()