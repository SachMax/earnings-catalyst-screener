"""Populate remaining rule-based features for upcoming earnings events."""
import math
import sqlite3
import time
from contextlib import closing
from datetime import date
from pathlib import Path

from features_library import (
    load_price_history,
    compute_volatility_percentile,
    compute_market_cap_features,
    compute_momentum_features,
    compute_volatility_features,
    compute_sector_relative_strength,
)

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "universe.db"
REQUEST_DELAY = 0.1

# Guidance is owned by feature_trifecta.py, not this script.
FEATURE_COLUMNS = {
    "vol_percentile": "REAL",
    "high_vol_regime": "INTEGER",
    "market_cap_bucket": "TEXT",
    "log_market_cap": "REAL",
    "return_20d": "REAL",
    "return_60d": "REAL",
    "return_120d": "REAL",
    "volatility_20d": "REAL",
    "volatility_60d": "REAL",
    "stock_vs_spy_20d": "REAL",
    "stock_vs_sector_20d": "REAL",
}


def ensure_columns(conn):
    """Add missing columns without hiding unexpected SQLite errors."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(features)")}
    if not {"ticker", "earnings_date"}.issubset(existing):
        raise RuntimeError("Initialize the features table first.")
    for name, sql_type in FEATURE_COLUMNS.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE features ADD COLUMN {name} {sql_type}")


def calculate_features(ticker, earnings_date, prices):
    values = dict.fromkeys(FEATURE_COLUMNS)
    if prices is None or prices.empty:
        return values

    # Reuse the original calculations; do not change the historical ML library.
    results = (
        compute_volatility_percentile(ticker, earnings_date, prices),
        compute_market_cap_features(ticker, earnings_date, prices),
        compute_momentum_features(earnings_date, prices),
        compute_volatility_features(earnings_date, prices),
        compute_sector_relative_strength(ticker, earnings_date, prices),
    )
    for result in results:
        if result is not None:
            for name in FEATURE_COLUMNS:
                if name in result:
                    values[name] = result[name]

    # Normalize numeric values for SQLite, including NumPy scalars and NaN.
    for name, sql_type in FEATURE_COLUMNS.items():
        value = values[name]
        if value is None or sql_type == "TEXT":
            continue
        value = float(value)
        values[name] = (
            (int(value) if sql_type == "INTEGER" else value)
            if math.isfinite(value) else None
        )
    return values


def main():
    if not DB_PATH.is_file():
        raise FileNotFoundError(DB_PATH)

    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute("PRAGMA busy_timeout = 5000")
        with conn:
            ensure_columns(conn)
            # Keep the original scope: all future events, not only seven days.
            conn.execute("""
                INSERT OR IGNORE INTO features (ticker, earnings_date)
                SELECT ticker, earnings_date FROM earnings_calendar
                WHERE earnings_date > date('now')
            """)

        events = conn.execute("""
            SELECT DISTINCT ticker, earnings_date FROM earnings_calendar
            WHERE earnings_date > date('now')
            ORDER BY ticker, earnings_date
        """).fetchall()
        print(f"Updating remaining features for {len(events)} upcoming events...", flush=True)

        # Sorted events let us load price history once per ticker without
        # retaining every ticker's full history in memory.
        previous_ticker = None
        prices = None
        no_prices = 0
        coverage = dict.fromkeys(FEATURE_COLUMNS, 0)
        assignments = ", ".join(f"{name} = ?" for name in FEATURE_COLUMNS)
        sql = f"UPDATE features SET {assignments} WHERE ticker = ? AND earnings_date = ?"

        for ticker, earnings_date in events:
            if ticker != previous_ticker:
                prices = load_price_history(ticker)
                previous_ticker = ticker

            if prices is None or prices.empty:
                no_prices += 1
                print(f"{ticker}: no prices; clearing remaining features", flush=True)

            values = calculate_features(ticker, date.fromisoformat(earnings_date), prices)
            with conn:
                conn.execute(sql, (*[values[name] for name in FEATURE_COLUMNS], ticker, earnings_date))

            for name, value in values.items():
                coverage[name] += int(value is not None)
            print(f"{ticker} | {earnings_date}: {sum(v is not None for v in values.values())}/{len(FEATURE_COLUMNS)} available", flush=True)
            time.sleep(REQUEST_DELAY)

        print(f"Remaining features: {len(events)} events updated; {no_prices} without prices.")
        for name, count in coverage.items():
            print(f"  {name}: {count}/{len(events)}")


if __name__ == "__main__":
    main()
