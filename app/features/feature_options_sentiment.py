"""Calculate ATM option sentiment for upcoming earnings events.

Run from the project environment:
    python app/features/feature_options_sentiment.py

Missing/unavailable option data is stored as SQL NULL rather than zero.
"""

import math
import sqlite3
import time
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "universe.db"
REQUEST_DELAY = 0.3


def safe_float(value):
    """Return a finite float or None (SQLite NULL)."""
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def find_atm_option(options_df, stock_price):
    """Return the option closest to the current stock price, or None."""
    if options_df is None or options_df.empty or "strike" not in options_df:
        return None

    strikes = pd.to_numeric(options_df["strike"], errors="coerce")
    differences = (strikes - stock_price).abs().dropna()
    if differences.empty:
        return None
    return options_df.loc[differences.idxmin()]


def calculate_option_ratios(ticker, earnings_date):
    """Return (call/put ATM volume, put/call ATM ask-price skew)."""
    stock = yf.Ticker(ticker)
    expirations = stock.options

    if not expirations:
        print(f"{ticker}: no option expirations available")
        return None, None

    eligible_expirations = [
        expiration for expiration in expirations
        if date.fromisoformat(expiration) >= earnings_date
    ]
    if not eligible_expirations:
        print(f"{ticker}: no options expiration on/after earnings date")
        return None, None

    expiration = min(eligible_expirations)
    chain = stock.option_chain(expiration)

    # Use the reported market price, falling back to recent closing prices.
    current_price = None
    try:
        info = stock.info or {}
        current_price = safe_float(info.get("currentPrice"))
        if current_price is None:
            current_price = safe_float(info.get("regularMarketPrice"))
    except Exception as exc:
        print(f"{ticker}: quote lookup failed ({exc}); trying recent close")

    if current_price is None or current_price <= 0:
        history = stock.history(period="5d")
        if not history.empty and "Close" in history:
            current_price = safe_float(history["Close"].iloc[-1])

    if current_price is None or current_price <= 0:
        print(f"{ticker}: stock price unavailable")
        return None, None

    atm_call = find_atm_option(chain.calls, current_price)
    atm_put = find_atm_option(chain.puts, current_price)
    if atm_call is None or atm_put is None:
        print(f"{ticker}: ATM option data unavailable")
        return None, None

    call_volume = safe_float(atm_call.get("volume"))
    put_volume = safe_float(atm_put.get("volume"))
    call_ask = safe_float(atm_call.get("ask"))
    put_ask = safe_float(atm_put.get("ask"))

    call_put_volume_ratio = None
    if call_volume is not None and put_volume is not None and call_volume > 0 and put_volume > 0:
        call_put_volume_ratio = round(call_volume / put_volume, 2)

    put_call_price_skew = None
    if call_ask is not None and put_ask is not None and call_ask > 0 and put_ask > 0:
        put_call_price_skew = round(put_ask / call_ask, 2)

    return call_put_volume_ratio, put_call_price_skew


def main():
    with sqlite3.connect(DB_PATH, timeout=30) as conn:
        conn.execute("PRAGMA busy_timeout = 5000")

        conn.execute("""
            INSERT OR IGNORE INTO features (ticker, earnings_date)
            SELECT ticker, earnings_date
            FROM earnings_calendar
            WHERE earnings_date > date('now')
        """)

        existing_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(features)")
        }
        for column in ("call_put_volume_ratio", "put_call_price_skew"):
            if column not in existing_columns:
                conn.execute(f"ALTER TABLE features ADD COLUMN {column} REAL")
        conn.commit()

        upcoming = conn.execute("""
            SELECT DISTINCT ticker, earnings_date
            FROM earnings_calendar
            WHERE earnings_date > date('now')
            ORDER BY earnings_date, ticker
        """).fetchall()

        print(f"Processing {len(upcoming)} upcoming earnings events...")
        missing_count = 0
        error_count = 0

        for i, (ticker, earnings_date_str) in enumerate(upcoming, start=1):
            earnings_date = date.fromisoformat(earnings_date_str)
            call_put_ratio = None
            put_call_skew = None

            try:
                call_put_ratio, put_call_skew = calculate_option_ratios(
                    ticker, earnings_date
                )
            except Exception as exc:
                # Unavailable/failed API data must not leave a stale value in the table.
                error_count += 1
                print(f"{ticker}: option data error: {exc}")
            finally:
                time.sleep(REQUEST_DELAY)

            call_put_ratio = safe_float(call_put_ratio)
            put_call_skew = safe_float(put_call_skew)

            print(f"[{i}/{len(upcoming)}] {ticker}: call/put volume ratio = {call_put_ratio}")
            print(f"{ticker}: put/call price skew = {put_call_skew}")

            if call_put_ratio is None:
                print("Volume data unavailable")
            elif call_put_ratio > 1.5:
                print("Bullish")
            elif call_put_ratio > 1.0:
                print("Neutral")
            else:
                print("Bearish")

            if put_call_skew is None:
                print("Skew data unavailable")
            elif put_call_skew <= 1.5:
                print("Pass")
            elif put_call_skew <= 2.0:
                print("Reduce conviction")
            else:
                print("Skip trade")

            # SQLite maps Python None to SQL NULL.
            conn.execute("""
                UPDATE features
                SET call_put_volume_ratio = ?,
                    put_call_price_skew = ?
                WHERE ticker = ? AND earnings_date = ?
            """, (
                call_put_ratio,
                put_call_skew,
                ticker,
                earnings_date_str,
            ))
            conn.commit()

            if call_put_ratio is None and put_call_skew is None:
                missing_count += 1

        print("\n========== OPTIONS SENTIMENT SUMMARY ==========")
        print(f"Events checked: {len(upcoming)}")
        print(f"Events with neither ratio available: {missing_count}")
        print(f"Ticker/API processing errors: {error_count}")


if __name__ == "__main__":
    main()
