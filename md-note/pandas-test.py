import sqlite3, edgar

edgar.set_identity("sachiomaximilliano166@gmail.com")
conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

ticker = "MSFT"
company = edgar.Company(ticker)
filings = company.get_filings(form="8-K")
inserted = 0

for f in filings.head(10):          # only look at the first 10
    if f.items and '2.02' in f.items:
        filing_date = f.filing_date.date() if hasattr(f.filing_date, 'date') else f.filing_date
        print(f"Inserting {filing_date}")
        c.execute("""
            INSERT OR REPLACE INTO earnings_calendar
            (ticker, earnings_date, eps_estimate, revenue_estimate)
            VALUES (?, ?, NULL, NULL)
        """, (ticker, filing_date.strftime('%Y-%m-%d')))
        inserted += 1

conn.commit()
print(f"Inserted {inserted} rows. Now checking count:")
c.execute("SELECT COUNT(*) FROM earnings_calendar WHERE ticker='MSFT' AND earnings_date < date('now')")
print("MSFT past rows:", c.fetchone()[0])
conn.close()