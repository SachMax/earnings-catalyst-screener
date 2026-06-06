import sqlite3
import pandas as pd
from datetime import date, timedelta
from features_library import *

conn = sqlite3.connect('data/universe.db')
conn.execute("PRAGMA busy_timeout = 5000")   # wait up to 5 seconds if locked
c = conn.cursor()

# =============================================================================
# 1. Add all new columns to ml_dataset (only if they don't exist)
# =============================================================================
columns = [
    ('quality_curr', 'INTEGER'), ('score_curr', 'INTEGER'),
    ('revenue_latest', 'REAL'), ('revenue_prev', 'REAL'),
    ('gm_change_bps', 'REAL'), ('sbc_pct_curr', 'REAL'),
    ('ocf_ni_ratio', 'REAL'), ('fcf_positive', 'INTEGER'),
    ('revenue_beat', 'INTEGER'), ('eps_beat_curr', 'INTEGER'),
    ('gaap_profit', 'INTEGER'),

    ('hist_quality', 'INTEGER'), ('avg_gm', 'REAL'),
    ('avg_sbc', 'REAL'), ('avg_ocf', 'REAL'),
    ('fcf_pos_count', 'INTEGER'), ('yoy_growth_streak', 'INTEGER'),
    ('scs_market_punishing', 'INTEGER'), ('scs_monetisation_evidence', 'INTEGER'),
    ('scs_conviction_penalty', 'TEXT'), ('scs_capex_trigger', 'INTEGER'),

    ('runup', 'REAL'), ('rsi', 'REAL'), ('volume_ratio', 'REAL'),

    ('surge_hold_count', 'INTEGER'), ('fade_count', 'INTEGER'),
    ('drop_count', 'INTEGER'), ('past_earnings_action', 'TEXT'),
    ('pct_surge', 'REAL'), ('pullback_bounce_count', 'INTEGER'),
    ('avg_pullback_depth', 'REAL'), ('past_pullback_bounce', 'TEXT'),
    ('post_earnings_drift', 'REAL'),

    ('guidance_valid', 'INTEGER'), ('sector_relative_strength', 'REAL'),
    ('sue', 'REAL'), ('hist_runup_avg', 'REAL'),
    ('seasonality_match', 'INTEGER'), ('pct_from_52w_low', 'REAL'),
    ('eps_streak', 'INTEGER'), ('revenue_streak', 'INTEGER'),
    ('vix_level', 'REAL'), ('oil_move_1d', 'REAL'),

    ('analyst_consensus', 'INTEGER'),

    ('insider_flag', 'INTEGER'), ('insider_net_value', 'REAL'),
    ('insider_buy_count', 'INTEGER'), ('insider_sell_count', 'INTEGER')
]

for col, col_type in columns:
    try:
        c.execute(f"ALTER TABLE ml_dataset ADD COLUMN {col} {col_type}")
    except sqlite3.OperationalError:
        pass
conn.commit()

# =============================================================================
# 2. Load rows that still need features – only for tickers with upcoming earnings
# =============================================================================
df = pd.read_sql("""
    SELECT * FROM ml_dataset
    WHERE quality_curr IS NULL
""", conn, parse_dates=['earnings_date'])

# Then apply the upcoming‑ticker filter (same as before)
today = date.today()
cutoff = today + timedelta(days=7)
upcoming_df = pd.read_sql("""
    SELECT DISTINCT ticker
    FROM earnings_calendar
    WHERE earnings_date BETWEEN date('now') AND ?
""", conn, params=(cutoff.strftime("%Y-%m-%d"),))
upcoming_tickers = upcoming_df['ticker'].tolist()

df = df[df['ticker'].isin(upcoming_tickers)]
df = df[df['quality_curr'].isna()]
print(f"Processing {len(df)} historical rows for these tickers")

# =============================================================================
# 3. Helper to safely extract a scalar or dictionary value
# =============================================================================
def safe_get(val, key=None):
    """If val is a dict, return val[key] (or val itself if key is None).
    If val is a scalar, return it directly. Otherwise return None."""
    if isinstance(val, dict):
        return val.get(key) if key else None
    return val

# =============================================================================
# 4. Cache price history and earnings dates per ticker
# =============================================================================
ticker_cache = {}

for counter, (idx, row) in enumerate(df.iterrows(), 1):
    if counter % 100 == 0:
        print(f"Processed {counter} rows...")

    ticker = row['ticker']
    ed = row['earnings_date'].date()

    # Load ticker‑specific data once
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

    # ---- Call every feature function ----
    curr     = current_earnings_quality(ticker, ed)
    hist     = historical_earnings_quality(ticker, ed)
    runup    = compute_runup(ticker, ed, df_price)
    rsi      = compute_rsi(ticker, ed, df_price)
    vol_rat  = compute_volume_ratio(ticker, ed, df_price)
    past     = compute_past_earnings_action(ticker, ed, df_price, ed_series)
    guidance = compute_guidance_valid(ticker, ed)
    sec_rel  = compute_sector_relative_strength(ticker, ed)
    sue      = compute_sue(ticker, ed)
    hist_run = compute_historical_runup_avg(ticker, ed, df_price, ed_series)
    season   = compute_seasonality_match(ticker, ed, df_price, ed_series)
    streaks  = compute_eps_rev_streak(ticker, ed, ed_series)
    market   = get_market_context(ed)
    pct_52w  = compute_pct_from_52wlow(ticker, ed, df_price)

    # Analyst consensus proxy
    mom = analyst_momentum(ticker, ed)
    consensus_proxy = None
    if mom and mom.get('net_analyst_momentum') is not None:
        consensus_proxy = 1 if mom['net_analyst_momentum'] > 0 else 0

    # ---- Update the database ----
    c.execute("""
        UPDATE ml_dataset SET
            quality_curr = ?, score_curr = ?, revenue_latest = ?, revenue_prev = ?,
            gm_change_bps = ?, sbc_pct_curr = ?, ocf_ni_ratio = ?, fcf_positive = ?,
            revenue_beat = ?, eps_beat_curr = ?, gaap_profit = ?,
            hist_quality = ?, avg_gm = ?, avg_sbc = ?, avg_ocf = ?,
            fcf_pos_count = ?, yoy_growth_streak = ?,
            scs_market_punishing = ?, scs_monetisation_evidence = ?,
            scs_conviction_penalty = ?, scs_capex_trigger = ?,
            runup = ?, rsi = ?, volume_ratio = ?,
            surge_hold_count = ?, fade_count = ?, drop_count = ?,
            past_earnings_action = ?, pct_surge = ?,
            pullback_bounce_count = ?, avg_pullback_depth = ?,
            past_pullback_bounce = ?, post_earnings_drift = ?,
            guidance_valid = ?, sector_relative_strength = ?, sue = ?,
            hist_runup_avg = ?, seasonality_match = ?,
            eps_streak = ?, revenue_streak = ?,
            vix_level = ?, oil_move_1d = ?,
            pct_from_52w_low = ?,
            analyst_consensus = ?
        WHERE ticker = ? AND earnings_date = ?
    """, (
        safe_get(curr, 'quality'), safe_get(curr, 'score'),
        safe_get(curr, 'revenue_latest'), safe_get(curr, 'revenue_prev'),
        safe_get(curr, 'gm_change_bps'), safe_get(curr, 'sbc_pct'),
        safe_get(curr, 'ocf_ni_ratio'), safe_get(curr, 'fcf_positive'),
        safe_get(curr, 'revenue_beat'), safe_get(curr, 'eps_beat'),
        safe_get(curr, 'gaap_profit'),
        safe_get(hist, 'quality'), safe_get(hist, 'avg_gm'),
        safe_get(hist, 'avg_sbc'), safe_get(hist, 'avg_ocf'),
        safe_get(hist, 'fcf_pos_count'), safe_get(hist, 'yoy_growth_streak'),
        safe_get(hist, 'scs_market_punishing_capex'),
        safe_get(hist, 'scs_monetisation_evidence'),
        safe_get(hist, 'scs_conviction_penalty'),
        safe_get(hist, 'scs_capex_trigger_active'),
        safe_get(runup), safe_get(rsi), safe_get(vol_rat),
        safe_get(past, 'surge_hold_count'), safe_get(past, 'fade_count'),
        safe_get(past, 'drop_count'), safe_get(past, 'past_earnings_action'),
        safe_get(past, 'pct_surge'), safe_get(past, 'pullback_bounce_count'),
        safe_get(past, 'avg_pullback_depth'), safe_get(past, 'past_pullback_bounce'),
        safe_get(past, 'post_earnings_drift'),
        safe_get(guidance), safe_get(sec_rel), safe_get(sue),
        safe_get(hist_run), safe_get(season),
        safe_get(streaks, 'eps_streak'), safe_get(streaks, 'revenue_streak'),
        safe_get(market, 'vix_level'), safe_get(market, 'oil_move_1d'),
        safe_get(pct_52w),
        consensus_proxy,
        ticker, ed.strftime('%Y-%m-%d')
    ))
    conn.commit()

print("Historical features added to ml_dataset.")
conn.close()