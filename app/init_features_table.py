import sqlite3

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS features (
    ticker TEXT,
    earnings_date TEXT,
    runup REAL,
    rsi REAL,
    short_interest REAL,
    implied_move REAL,
    recommendationKey TEXT,
    recommendationMean REAL,
    PRIMARY KEY (ticker, earnings_date)
)
""")
conn.commit()
conn.close()