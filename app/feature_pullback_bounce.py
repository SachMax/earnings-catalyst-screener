import sqlite3
import pandas as pd
from datetime import date, timedelta
import yfinance as yf
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
    c.execute("ALTER TABLE features ADD COLUMN past_pullback_bounce TEXT;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN pullback_bounce_count INTEGER;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN avg_pullback_depth real;")
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
            reactions = []
            pullback_bounce_sum = 0
            for _,erow in recent.iterrows():
                hist_date = erow.name.date()
                d1 = hist_date + timedelta(days=1)

                
                try:                    
                    idx1 = df.index.get_indexer([d1], method="bfill")[0]
                    window20 = df.iloc[idx1 : idx1 + 20]
                    if len(window20) < 20:
                        continue

                    # 1. Post‑earnings high (first 5 days)
                    first5 = window20.iloc[:5]
                    post_high = first5['close_price'].max()

                    # Find the first date in first5 that hit this high
                    high_date = first5[first5['close_price'] == post_high].index[0]
                    # Convert that date label to a positional index within window20
                    high_pos = window20.index.get_loc(high_date)

                    # 2. Lowest close after that high
                    remaining = window20.iloc[high_pos + 1:]
                    if remaining.empty:
                        continue
                    pull_back = remaining['close_price'].min()
                    final_close = window20['close_price'].iloc[-1]
                    pullback_pct = (pull_back - post_high) / post_high
                    if pullback_pct <= -0.02 and final_close > post_high:
                        label = "pullback and bounce"
                        reactions.append(label)
                        pullback_bounce_sum += pullback_pct
                    else:
                        label = "no bounce"
                        reactions.append(label)
                except Exception as t:
                    print(f"{ticker}: error - {t}")
                    continue
            total = len(reactions)
            pullback_bounce_count = None
            pull_back_avg = None
            if total > 0:
                pullback_bounce_count = reactions.count("pullback and bounce")
                if pullback_bounce_count > 0 and pullback_bounce_sum != 0:
                    pull_back_avg = round((pullback_bounce_sum * 100) / pullback_bounce_count, 2) 
            else:
                pass

        except Exception as o:
            print(f"{ticker}: error -> {o}")
            continue
        if len(reactions) < 2:
            print(f"{ticker}: not enough data, skipping...")
            continue
        most_common = max(reactions, key=reactions.count)
        print(f"{ticker}: pullback and bounce probability = {most_common} from {reactions}")
    except Exception as e:
        print(f"{ticker}: error -> {e}")
        continue
    if pullback_bounce_count is not None:
        c.execute("UPDATE features SET pullback_bounce_count = ? WHERE ticker = ? AND earnings_date = ?",
        (pullback_bounce_count, ticker, ed_clean.strftime("%Y-%m-%d")))
    if pull_back_avg is not None:
        print(f"pullback bounce avg = {pull_back_avg}")
        c.execute("UPDATE features SET avg_pullback_depth = ? WHERE ticker = ? AND earnings_date = ?",
        (pull_back_avg, ticker, ed_clean.strftime("%Y-%m-%d")))
    if most_common is not None:
        c.execute("UPDATE features SET past_pullback_bounce = ? WHERE ticker = ? AND earnings_date = ?",
          (most_common, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()