import sqlite3
import pandas as pd
from datetime import date, timedelta
import yfinance as yf

sector_to_etf = {
    "Financial Services": "XLF",
    "Technology": "XLK",
    "Consumer Defensive": "XLP",
    "Consumer Cyclical": "XLY",
    "Healthcare": "XLV",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Basic Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
    "Consumer Staples": "XLP"  # another name for Consumer Defensive
}

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

try:
    c.execute("ALTER TABLE features ADD COLUMN sector_relative_strength REAL;")
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
            c.execute("SELECT sector FROM features WHERE ticker = ? and earnings_date = ?", (ticker, ed_clean.strftime("%Y-%m-%d")))
            irow = c.fetchone()
            if irow is None:
                print(f"{ticker}: no sector data")
                continue
            sector = irow[0]
            etf_ticker = sector_to_etf.get(sector)
            if etf_ticker is None:
                print(f"{ticker}: ETF_ticker not found")
                continue
            
            sector_hist = yf.Ticker(etf_ticker).history(period="1mo")
            spy_hist    = yf.Ticker("SPY").history(period="1mo")

            if len(sector_hist) < 2 or len(spy_hist) < 2:
                print(f"{ticker}: not enough trading data, skipping")
                continue

            # Use only the last 20 trading days
            sector_hist = sector_hist.tail(20)
            spy_hist    = spy_hist.tail(20)

            # Extract closing prices as plain numbers
            sector_start = sector_hist['Close'].iloc[0]
            sector_end   = sector_hist['Close'].iloc[-1]
            spy_start    = spy_hist['Close'].iloc[0]
            spy_end      = spy_hist['Close'].iloc[-1]

            # Percentage returns
            sector_return = ((sector_end - sector_start) / sector_start) * 100
            spy_return    = ((spy_end - spy_start) / spy_start) * 100

            relative_strength = round(sector_return - spy_return, 2)

        except Exception as o:
            print(f"{ticker}: error -> {o}")
            continue
        print(f"{ticker}: sector relative strength -> {relative_strength}")
        if relative_strength < 0:
            print("sector is under headwind / not strong")
        else:
            print("sector is under tailwind / strong")
    except Exception as e:
        print(f"{ticker}: error -> {e}")
        continue
    c.execute("UPDATE features SET sector_relative_strength = ? WHERE ticker = ? AND earnings_date = ?",
          (relative_strength, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()