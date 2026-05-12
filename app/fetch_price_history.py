import sqlite3
import yfinance as yf

# Connect to the database
conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute (
    """ 
    CREATE TABLE IF NOT EXISTS price_history (
    ticker TEXT, date TEXT, close_price REAL, volume INTEGER, PRIMARY KEY (ticker, date))
"""
)

pep = yf.Ticker("PEP")
pep_5y = pep.history(period="5y")

inserted_rows=0
for index, row in pep_5y.iterrows():
    hist_date = index.strftime("%Y-%m-%d")
    hist_close_price = float(row["Close"])
    hist_volume_number = int(row["Volume"])
    c.execute("INSERT OR REPLACE INTO price_history VALUES (?, ?, ?, ?)", ("PEP", hist_date, hist_close_price, hist_volume_number))
    inserted_rows+=1

print(f"Rows inserted {inserted_rows}")
conn.commit()
conn.close()