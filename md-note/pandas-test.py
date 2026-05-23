import sqlite3

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()
c.execute("SELECT ticker, earnings_date FROM earnings_calendar WHERE ticker='PEP' ORDER BY earnings_date DESC LIMIT 1")
row = c.fetchone()
print("Row from DB:", row)
conn.close()