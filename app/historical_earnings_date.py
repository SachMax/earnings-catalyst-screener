import sqlite3
import edgar
import pandas as pd
from datetime import date

edgar.set_identity("sachiomaximilliano166@gmail.com")

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute("""
    CREATE TABLE IF NOT EXISTS earnings_history (
        ticker TEXT,
        earnings_date TEXT,
        PRIMARY KEY (ticker, earnings_date)
    )
""")

tickers_df = pd.read_csv('data/us_stocks.csv')
tickers = tickers_df['Symbol'].tolist()

for ticker in tickers:
    try:
        company = edgar.Company(ticker)
        filings = company.get_filings(form="8-K")  # ALL filings, not just head
        inserted = 0
        for f in filings:
            if f.items and '2.02' in str(f.items):
                filing_date = f.filing_date.date() if hasattr(f.filing_date, 'date') else f.filing_date
                c.execute(
                    "INSERT OR IGNORE INTO earnings_history (ticker, earnings_date) VALUES (?, ?)",
                    (ticker, filing_date.strftime('%Y-%m-%d'))
                )
                inserted += 1
        conn.commit()
        print(f"{ticker}: {inserted} historical dates inserted")
    except Exception as e:
        print(f"{ticker} error: {e}")

# Verify
c.execute("SELECT COUNT(*) FROM earnings_history")
total = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM earnings_history WHERE earnings_date < date('now')")
past = c.fetchone()[0]
print(f"Total rows in earnings_history: {total}, Past rows: {past}")
conn.close()