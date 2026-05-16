import sqlite3
import pandas as pd
from datetime import date, timedelta


conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS features (
    ticker TEXT,
    earnings_date TEXT,
    runup REAL,
    PRIMARY KEY (ticker, earnings_date)
)
""")


today = date.today()
df_ed = pd.read_sql(
    "SELECT * FROM earnings_calendar WHERE earnings_date > ?",
    conn,
    params=(today.strftime("%Y-%m-%d"),),
    parse_dates='earnings_date'
)

def get_close(df, target):
    try:
        return df.loc[target, 'close_price']
    except KeyError:
        idx_14d = df.index.get_indexer([target], method='ffill')[0]
        return df.iloc[idx_14d]['close_price']

for index,row in df_ed.iterrows(): 
    ticker = row['ticker']
    ed_clean = row['earnings_date'].date()
    df_price = pd.read_sql(f"SELECT * FROM price_history WHERE ticker='{ticker}' ORDER BY date", conn, parse_dates='date', index_col='date')

    date_14d_before = ed_clean - timedelta(days=14)
    date_2d_before = ed_clean - timedelta(days=2)

    if df_price.empty: 
        print(f"no data in {ticker}, skipping...")
        continue
    last_date = df_price.index[-1].date()
    if date_14d_before > last_date:
        print(f"{ticker} -- not enough data, skipping...")
        continue
    # 14 days before
            

    close_14d_before = get_close(df_price, date_14d_before)
    close_2d_before = get_close(df_price, date_2d_before)

    print(f"\nClose price on {date_14d_before}: {close_14d_before}")
    print(f"Close price on {date_2d_before}: {close_2d_before}")

    runup = (close_2d_before - close_14d_before) / close_14d_before
    runup = round(runup * 100, 2)
    print(f"Pre-earnings run-up for {ticker}: {runup}")

    print(f"\ninserting data to database...")
    c.execute("UPDATE features SET runup = ? WHERE ticker = ? AND earnings_date = ?",
          (runup, ticker, ed_clean.strftime("%Y-%m-%d")))

    # If no row existed (c.rowcount == 0), insert a new one
    if c.rowcount == 0:
        c.execute("""
            INSERT OR REPLACE INTO features (ticker, earnings_date, runup, rsi, short_interest)
            VALUES (?, ?, ?, NULL, NULL)
        """, (ticker, ed_clean.strftime("%Y-%m-%d"), runup))
        conn.commit()
conn.close()