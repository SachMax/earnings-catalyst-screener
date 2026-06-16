import sqlite3
import yfinance as yf

# Connect to the database (creates the file if it doesn't exist)
conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

# Create the ticker_master table
c.execute('''
    CREATE TABLE IF NOT EXISTS ticker_master (
        ticker TEXT PRIMARY KEY,
        company_name TEXT
    )
''')

# Pull PEP stock data
pep = yf.Ticker("PEP")
hist = pep.history(period="5d")
print("PEP data pulled successfully!")
print(hist.head())

# Store the ticker in the master table
c.execute("INSERT OR REPLACE INTO ticker_master VALUES ('PEP', 'PepsiCo')")
conn.commit()
conn.close()