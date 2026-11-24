"""Populate rule-based run-up using the existing shared calculation."""
from pathlib import Path
import sqlite3
from contextlib import closing

from features_library import compute_runup, load_price_history

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "universe.db"


def main():
    if not DB_PATH.is_file():
        raise FileNotFoundError(DB_PATH)
    with closing(sqlite3.connect(DB_PATH)) as conn, conn:
        conn.execute("PRAGMA busy_timeout = 5000")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(features)")}
        if not columns:
            raise RuntimeError("Run app/init_features_table.py first.")
        if "runup" not in columns:
            conn.execute("ALTER TABLE features ADD COLUMN runup REAL")

        events = conn.execute("""
            SELECT DISTINCT ticker, earnings_date
            FROM earnings_calendar
            WHERE earnings_date > date('now')
            ORDER BY ticker, earnings_date
        """).fetchall()
        # Load prices only once per ticker. No external API requests are needed.
        previous_ticker = None
        prices = None
        rows = []
        for ticker, earnings_date in events:
            if ticker != previous_ticker:
                prices = load_price_history(ticker)
                previous_ticker = ticker
            value = compute_runup(ticker, earnings_date, prices)
            rows.append((ticker, earnings_date, value))

        # Upsert only the runup column; write NULL if the calculation is unavailable.
        conn.executemany("""
            INSERT INTO features (ticker, earnings_date, runup)
            VALUES (?, ?, ?)
            ON CONFLICT(ticker, earnings_date) DO UPDATE SET runup = excluded.runup
        """, rows)
        available = sum(value is not None for _, _, value in rows)
        print(f"Run-up: {available}/{len(rows)} events populated; "
              f"{len(rows) - available} unavailable.")


if __name__ == "__main__":
    main()