import sqlite3
import pandas as pd
from datetime import date, timedelta
import yfinance as yf
import numpy as np

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

try:
    c.execute("ALTER TABLE features ADD COLUMN seasonality_match INTEGER;")
except sqlite3.OperationalError:
    pass   # column already exists

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
            c.execute("SELECT runup FROM features WHERE ticker = ? and earnings_date = ?", (ticker, ed_clean.strftime("%Y-%m-%d")))
            irow = c.fetchone()
            if irow is None:
                print(f"{ticker}: no pre-earnings run-up data")
                continue
            runup = irow[0]
            if runup is None:
                print(f"{ticker}: run-up data not found")
                continue
            
            stock = yf.Ticker(ticker)
            earnings_hist = stock.earnings_dates
            if earnings_hist.empty or earnings_hist is None:
                print(f"{ticker}: no earnings history data, skipping")
                continue
            earnings_hist.index = earnings_hist.index.tz_localize(None)
            past_earnings = earnings_hist[earnings_hist.index <= pd.Timestamp(today)]
            if len(past_earnings) < 2:
                print(f"{ticker}: not enough past earnings, skipping")
                continue

            recent = past_earnings.sort_index().tail(4)
            
            historical_runup = []
            for _,erow in recent.iterrows():
                hist_date = erow.name.date()
                d14 = hist_date - timedelta(days=14)
                d2 = hist_date - timedelta(days=2)

                last_available = df.index[-1].date()
                if d14 < df.index[0].date() or d2 > last_available:
                    continue
                
                try:
                    close14 = get_close(df, d14)
                    close2 = get_close(df, d2)
                    if close14 and close2 != 0:
                        historical_runup.append(((close2-close14)/close14)*100)
                    else:
                        continue
                except Exception as t:
                    print(f"{ticker}: error - {t}")
                    continue

        except Exception as o:
            print(f"{ticker}: error -> {o}")
            continue
        run_up_value = 0 # if 1 = positive, elif 0 = negative

        if len(historical_runup) < 2:
            print(f"{ticker}: not enough historical run‑up samples, skipping")
            continue
        past_runup_mean = round(float(np.mean(historical_runup)), 2)
        if (past_runup_mean > 0 and runup > 0) or (past_runup_mean < 0 and runup < 0):
            run_up_value = 1
            print(f"{ticker}: past run-up aligns with current run-up")
        else:
            run_up_value = 0
            print(f"{ticker}: past run-up doesn't align with current run-up")
    except Exception as e:
        print(f"{ticker}: error -> {e}")
        continue
    c.execute("UPDATE features SET seasonality_match = ? WHERE ticker = ? AND earnings_date = ?",
          (run_up_value, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()