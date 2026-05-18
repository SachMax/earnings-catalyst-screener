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
    valuation_pe REAL,
    sector TEXT,
    eps_streak INTEGER,
    sue REAL,
    volume_confirmation REAL,
    post_earnings_drift REAL,
    PRIMARY KEY (ticker, earnings_date)
)
""")
conn.commit()
conn.close()