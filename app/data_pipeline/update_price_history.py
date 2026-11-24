
import pandas as pd
import sqlite3
import yfinance as yf
import time
import math
import argparse

from datetime import date, timedelta

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------
TICKERS_PATH = "data/us_stocks.csv"

LOOKBACK_DAYS = 120
TOLERANCE = 1e-8
REQUEST_DELAY = 0.3

parser = argparse.ArgumentParser()
parser.add_argument(
    "--rebuild",
    action="store_true",
    help="Delete and rebuild price_history from scratch"
)
parser.add_argument(
    "--full-refresh",
    action="store_true",
    help="Download maximum history without deleting existing data"
)
args = parser.parse_args()

# ---------------------------------------------------------
# Database connection
# ---------------------------------------------------------
conn = sqlite3.connect("data/universe.db")
conn.execute("PRAGMA busy_timeout = 5000")
c = conn.cursor()

if args.rebuild:
    print("Rebuilding price_history from scratch...")
    c.execute("DROP TABLE IF EXISTS price_history")

c.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        ticker TEXT,
        date TEXT,
        open REAL,
        high REAL,
        low REAL,
        close REAL,
        volume INTEGER,
        PRIMARY KEY (ticker, date)
    )
""")

conn.commit()

# ---------------------------------------------------------
# Load tickers
# ---------------------------------------------------------
df = pd.read_csv(TICKERS_PATH)

tickers = (
    df["Symbol"]
    .dropna()
    .astype(str)
    .str.strip()
    .drop_duplicates()
    .tolist()
)

tickers = [t for t in tickers if t]

print(f"Total tickers: {len(tickers)}")

total_written = 0
total_skipped = 0
failed_tickers = []

# ---------------------------------------------------------
# Fetch historical prices
# ---------------------------------------------------------
for i, ticker in enumerate(tickers, 1):

    if i == 1 or i % 100 == 0:
        print(f"Progress: {i}/{len(tickers)}")

    try:
        stock = yf.Ticker(ticker)

        # Get most recent date already in SQLite
        c.execute("""
            SELECT MAX(date)
            FROM price_history
            WHERE ticker = ?
        """, (ticker,))

        last_date = c.fetchone()[0]

        if last_date is None or args.full_refresh:
            # No history exists for this ticker
            hist = stock.history(
                period="max",
                auto_adjust=False,
                actions=True
            )
        else:
            # Download an overlapping recent period
            start_date = (
                date.fromisoformat(last_date)
                - timedelta(days=LOOKBACK_DAYS)
            ).isoformat()

            hist = stock.history(
                start=start_date,
                auto_adjust=False,
                actions=True
            )

            # Stock splits may change earlier prices
            if (
                not hist.empty
                and "Stock Splits" in hist.columns
                and (hist["Stock Splits"].fillna(0) != 0).any()
            ):
                print(f"{ticker}: split detected, refreshing full history")

                hist = stock.history(
                    period="max",
                    auto_adjust=False,
                    actions=True
                )

        if hist.empty:
            print(f"{ticker}: no data")
            continue

        # -------------------------------------------------
        # Prepare and validate observations
        # -------------------------------------------------
        rows = []
        skipped = 0

        for index, row in hist.iterrows():

            try:
                py_open = float(row["Open"])
                py_high = float(row["High"])
                py_low = float(row["Low"])
                py_close = float(row["Close"])
                py_volume = int(row["Volume"])

                prices = [
                    py_open,
                    py_high,
                    py_low,
                    py_close
                ]

                # Reject NaN and infinity
                if not all(math.isfinite(p) for p in prices):
                    skipped += 1
                    continue

                # Reject nonpositive prices
                if any(p <= 0 for p in prices):
                    skipped += 1
                    continue

                # Reject negative volume
                if py_volume < 0:
                    skipped += 1
                    continue

                # Floating-point tolerance
                scale = max(prices)
                tolerance = TOLERANCE * scale

                if (
                    py_high + tolerance <
                        max(py_open, py_low, py_close)
                    or
                    py_low - tolerance >
                        min(py_open, py_high, py_close)
                ):
                    skipped += 1
                    continue

                # Correct tiny rounding discrepancies
                py_high = max(
                    py_open, py_high, py_low, py_close
                )

                py_low = min(
                    py_open, py_high, py_low, py_close
                )

                rows.append((
                    ticker,
                    index.strftime("%Y-%m-%d"),
                    py_open,
                    py_high,
                    py_low,
                    py_close,
                    py_volume
                ))

            except (ValueError, TypeError, OverflowError):
                skipped += 1
                continue

        # -------------------------------------------------
        # Insert new rows / update existing rows
        # -------------------------------------------------
        changes_before = conn.total_changes

        c.executemany("""
            INSERT INTO price_history
            (ticker, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(ticker, date)
            DO UPDATE SET
                open = excluded.open,
                high = excluded.high,
                low = excluded.low,
                close = excluded.close,
                volume = excluded.volume

            WHERE
                price_history.open IS NOT excluded.open
                OR price_history.high IS NOT excluded.high
                OR price_history.low IS NOT excluded.low
                OR price_history.close IS NOT excluded.close
                OR price_history.volume IS NOT excluded.volume
        """, rows)

        conn.commit()

        written = conn.total_changes - changes_before

        total_written += written
        total_skipped += skipped

        if written > 0 or skipped > 0:
            print(
                f"{ticker}: {written} rows inserted/updated, "
                f"{skipped} rejected"
            )

    except Exception as e:
        conn.rollback()
        failed_tickers.append(ticker)
        print(f"{ticker}: ERROR - {e}")

    finally:
        time.sleep(REQUEST_DELAY)

# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------
print("\n========== SUMMARY ==========")
print(f"Rows inserted/updated: {total_written:,}")
print(f"Invalid observations skipped: {total_skipped:,}")
print(f"Failed tickers: {len(failed_tickers)}")

if failed_tickers:
    print("Failed ticker list:", failed_tickers)

c.execute("SELECT COUNT(*) FROM price_history")
total_rows = c.fetchone()[0]

c.execute("SELECT MAX(date) FROM price_history")
latest_date = c.fetchone()[0]

print(f"Total database rows: {total_rows:,}")
print(f"Latest stored date: {latest_date}")

conn.close()
