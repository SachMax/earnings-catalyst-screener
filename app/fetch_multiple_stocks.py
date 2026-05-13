import sqlite3
import yfinance as yf
import time

#connect to the database
conn = sqlite3.connect("data/universe.db")
c = conn.cursor()

c.execute (
    """ 
    CREATE TABLE IF NOT EXISTS price_history (
    ticker TEXT, date TEXT, close_price REAL, volume INTEGER, PRIMARY KEY (ticker, date))
"""
)

#list of stocks
inserted_rows = 0
tickers = ["PEP", "TSM", "GS", "AAPL", "MSFT", "JNJ", "JPM", "BAC", "WMT", "XOM"]
for i in tickers:
    ticker = yf.Ticker(i)
    hist = ticker.history(period="5y")
    if hist.empty:
        print(f"{i}: no data, skipping")
        continue

    for index, row in hist.iterrows():
        py_date = index.strftime("%Y-%m-%d")
        py_close = float(row['Close'])
        py_volume = int(row['Volume'])
        c.execute("INSERT OR REPLACE INTO price_history VALUES (?, ?, ?, ?)", (i, py_date, py_close, py_volume))
        inserted_rows += 1

    conn.commit()
    print(f"{i}: {len(hist)} rows inserted")
    time.sleep(0.5)   # pause between tickers
print(f"Total rows inserted across all tickers: {inserted_rows}")
conn.close()