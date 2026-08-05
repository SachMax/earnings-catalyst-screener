import sqlite3
import pandas as pd
from datetime import date, timedelta


conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

try:
    c.execute("ALTER TABLE features ADD COLUMN volume_confirmation REAL;")
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
            print(f"no data in {ticker}, skipping...")
            continue

        target_date = ed_clean + timedelta(days=1)
        idx = df.index.get_indexer([target_date], method= "ffill")[0]
        post_vol = df['volume'].iloc[idx]

        past_vol = df.loc[:ed_clean.strftime("%Y-%m-%d")].tail(20)['volume'].mean() #slicing only up to earnings_date
        if pd.isna(post_vol) or pd.isna(past_vol):
            print(f"{ticker}: not enough data")
            continue

        ratio = float(round(post_vol / past_vol, 2))
        
    except Exception as e:
        print(f"{ticker}: error -> {e}")
        continue
    print(f"{ticker}: ratio -> {ratio}")
    if ratio >= 1.5:
        print(": post-volume is confirmed")
    else:
        print(": post-volume is not confirmed")
    c.execute("UPDATE features SET volume_confirmation = ? WHERE ticker = ? AND earnings_date = ?",
          (ratio, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()