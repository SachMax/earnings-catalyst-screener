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
    c.execute("ALTER TABLE features ADD COLUMN iv_hv_ratio REAL;")
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

        try:
            c.execute("SELECT implied_move FROM features WHERE ticker = ? and earnings_date = ?", (ticker, ed_clean.strftime("%Y-%m-%d")))
            irow = c.fetchone()
            if irow is None:
                print(f"{ticker}: no IV data")
                continue
            im = irow[0] / 100
        except Exception as o:
            print(f"{ticker}: error -> {o}")
            continue
        df['daily_return'] = df['close_price'].pct_change()
        df['hv'] = df['daily_return'].rolling(20).std()
        hv = df['hv'].iloc[-1]
        if pd.isna(hv) or hv == 0:
            print(f"{ticker}: invalid HV (NaN or zero), skipping")
            continue
        
        ratio = float(round(im / hv, 2))
        print(f"{ticker}: IV/HV ratio -> {ratio}")
        if ratio >= 1.5:
            print("confirmed")
        else:
            print("not confirmed")
    except Exception as e:
        print(f"{ticker}: error -> {e}")
        continue
    c.execute("UPDATE features SET iv_hv_ratio = ? WHERE ticker = ? AND earnings_date = ?",
          (ratio, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()