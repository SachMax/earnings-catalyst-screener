import sqlite3
import pandas as pd
from datetime import date, timedelta

conn = sqlite3.connect("data/universe.db")
c = conn.cursor()  

c.execute("""
    CREATE TABLE IF NOT EXISTS ml_dataset (
        ticker TEXT,
        earnings_date TEXT,
        target_5d_drift REAL,
        PRIMARY KEY (ticker, earnings_date)
    )
""")
conn.commit()

today = date.today()
df_ed = pd.read_sql("""
    SELECT * FROM earnings_history
    WHERE earnings_date < ?
    ORDER BY earnings_date
""", conn, parse_dates=['earnings_date'], params=(today.strftime("%Y-%m-%d"),))

for index, row in df_ed.iterrows():
    ticker = row['ticker']
    ed_clean = row['earnings_date'].date()

    try:
        df = pd.read_sql(f"SELECT * FROM price_history WHERE ticker='{ticker}' ORDER BY date",
                         conn, parse_dates=['date'], index_col='date')
    except Exception as er:
        print(f"{ticker}: error loading price data – {er}")
        continue

    if df.empty:
        print(f"{ticker}: no price data")
        continue

    try:
        before = df.loc[:ed_clean].iloc[-1]
        close_before = before['close_price']
    except (KeyError, IndexError):
        print(f"{ticker}: no price on or before {ed_clean}")
        continue

    try:
        idx_start = df.index.get_loc(before.name)  
        idx_end = idx_start + 5                    
        if idx_end >= len(df):
            continue
        close_after = df.iloc[idx_end]['close_price']
    except:
        continue

    if close_before == 0:
        continue

    drift_pct = ((close_after - close_before) / close_before) * 100

    c.execute("""
        INSERT OR REPLACE INTO ml_dataset (ticker, earnings_date, target_5d_drift)
        VALUES (?, ?, ?)
    """, (ticker, ed_clean.strftime('%Y-%m-%d'), round(drift_pct, 4)))
    conn.commit()
    print(f"{ticker} {ed_clean}: drift = {round(drift_pct,2)}%")

conn.close()