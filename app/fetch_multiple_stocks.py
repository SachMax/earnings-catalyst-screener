import sqlite3
import yfinance as yf
import time
import pandas as pd

# Connect to the database
conn = sqlite3.connect("data/universe.db")
c = conn.cursor()

c.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        ticker TEXT,
        date TEXT,
        close_price REAL,
        volume INTEGER,
        PRIMARY KEY (ticker, date)
    )
""")

# Load ALL US stocks (not just S&P 500)
df = pd.read_csv("data/us_stocks.csv")
tickers = df['Symbol'].tolist()
print(f"Total tickers to process: {len(tickers)}")

inserted_rows = 0
for i, ticker in enumerate(tickers):
    if i % 100 == 0:
        print(f"Progress: {i}/{len(tickers)}")

    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="max")
        if hist.empty:
            print(f"{ticker}: no data, skipping")
            continue

        for index, row in hist.iterrows():
            py_date = index.strftime("%Y-%m-%d")
            py_close = float(row['Close'])
            py_volume = int(row['Volume'])
            c.execute(
                "INSERT OR REPLACE INTO price_history VALUES (?, ?, ?, ?)",
                (ticker, py_date, py_close, py_volume)
            )
            inserted_rows += 1

        conn.commit()
        print(f"{ticker}: {len(hist)} rows inserted")
        time.sleep(0.3)   # be gentle to Yahoo's servers

    except Exception as e:
        print(f"{ticker} - Error - {e}")

print(f"Total rows inserted across all tickers: {inserted_rows}")
conn.close()