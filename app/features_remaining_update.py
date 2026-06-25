# features_remaining_update.py
import sqlite3
import pandas as pd
from datetime import date, timedelta
import time
from features_library import *

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

# ---------------------------------------------------------------------------
# 1. Ensure all upcoming rows exist in features (from earnings_calendar)
# ---------------------------------------------------------------------------
c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

# ---------------------------------------------------------------------------
# 2. Add all new columns (if they don't already exist)
# ---------------------------------------------------------------------------
new_columns = [
    ('vol_percentile', 'REAL'),
    ('high_vol_regime', 'INTEGER'),
    ('market_cap_bucket', 'TEXT'),
    ('log_market_cap', 'REAL'),
    ('return_20d', 'REAL'),
    ('return_60d', 'REAL'),
    ('return_120d', 'REAL'),
    ('volatility_20d', 'REAL'),
    ('volatility_60d', 'REAL'),
    ('stock_vs_spy_20d', 'REAL'),
    ('stock_vs_sector_20d', 'REAL'),
    ('guidance_finbert_prob', 'REAL')
]

for col_name, col_type in new_columns:
    try:
        c.execute(f"ALTER TABLE features ADD COLUMN {col_name} {col_type}")
    except sqlite3.OperationalError:
        pass   # column already exists
conn.commit()

# ---------------------------------------------------------------------------
# 3. Load upcoming ticker/date pairs from earnings_calendar (next 7 days)
# ---------------------------------------------------------------------------

df = pd.read_sql("""
    SELECT ticker, earnings_date
    FROM earnings_calendar
    WHERE earnings_date > date('now')
""", conn, parse_dates=['earnings_date'])

if df.empty:
    print("No upcoming events in earnings_calendar.")
    conn.close()
    exit()

print(f"Updating {len(df)} upcoming events with new features...")

# ---------------------------------------------------------------------------
# 4. Cache price history & earnings dates per ticker
# ---------------------------------------------------------------------------
ticker_cache = {}

for idx, row in df.iterrows():
    ticker = row['ticker']
    ed = row['earnings_date'].date()
    if ticker not in ticker_cache:
        try:
            df_price = load_price_history(ticker)
            ed_series = load_earnings_dates(ticker)
            ticker_cache[ticker] = (df_price, ed_series)
        except:
            ticker_cache[ticker] = (pd.DataFrame(), pd.Series())
    df_price, ed_series = ticker_cache[ticker]

    if df_price.empty:
        continue

    # -------------------------------------------------------------------
    # Compute all new features using the shared library
    # -------------------------------------------------------------------
    vol_pct    = compute_volatility_percentile(ticker, ed, df_price)
    mcap_feats = compute_market_cap_features(ticker, ed, df_price)
    mom_feats  = compute_momentum_features(ed, df_price)
    vol_feats  = compute_volatility_features(ed, df_price)
    rel_str    = compute_sector_relative_strength(ticker, ed, df_price)
    guidance_prob = compute_guidance_bert(ticker, ed)

    def safe_val(d, k):
        if d is None:
            return None
        return d.get(k)
    print(vol_pct)
    print(mcap_feats)
    print(mom_feats)
    print(vol_feats)
    print(rel_str)
    print(f"{ticker}: inserted\n")
    c.execute("""
        UPDATE features SET
            vol_percentile = ?,
            high_vol_regime = ?,
            market_cap_bucket = ?,
            log_market_cap = ?,
            return_20d = ?,
            return_60d = ?,
            return_120d = ?,
            volatility_20d = ?,
            volatility_60d = ?,
            stock_vs_spy_20d = ?,
            stock_vs_sector_20d = ?,
            guidance_finbert_prob = ?
        WHERE ticker = ? AND earnings_date = ?
    """, (
        safe_val(vol_pct, 'vol_percentile'),
        safe_val(vol_pct, 'high_vol_regime'),
        safe_val(mcap_feats, 'market_cap_bucket'),
        safe_val(mcap_feats, 'log_market_cap'),
        safe_val(mom_feats, 'return_20d'),
        safe_val(mom_feats, 'return_60d'),
        safe_val(mom_feats, 'return_120d'),
        safe_val(vol_feats, 'volatility_20d'),
        safe_val(vol_feats, 'volatility_60d'),
        safe_val(rel_str, 'stock_vs_spy_20d'),
        safe_val(rel_str, 'stock_vs_sector_20d'),
        guidance_prob,
        ticker,
        ed.strftime('%Y-%m-%d')
    ))
    conn.commit()
    time.sleep(0.1)

conn.close()
print("All remaining features updated in the features table.")