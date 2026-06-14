import sqlite3
import pandas as pd
import time
from datetime import date, timedelta
from features_library import *

# ---------------------------------------------------------------------------
# Config – adjust BATCH_SIZE to whatever your daily capacity allows
# ---------------------------------------------------------------------------
BATCH_SIZE = 3000   # rows per run
DB_PATH = 'data/universe.db'

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA busy_timeout = 5000")
c = conn.cursor()

# ---------------------------------------------------------------------------
# 1. Ensure all feature columns exist (same as always)
# ---------------------------------------------------------------------------
columns = [
    ('quality_curr', 'INTEGER'), ('score_curr', 'INTEGER'),
    ('revenue_latest', 'REAL'), ('revenue_prev', 'REAL'),
    ('gm_change_bps', 'REAL'), ('sbc_pct_curr', 'REAL'),
    ('ocf_ni_ratio', 'REAL'), ('fcf_positive', 'INTEGER'),
    ('revenue_beat', 'INTEGER'), ('eps_beat_curr', 'INTEGER'),
    ('gaap_profit', 'INTEGER'),
    ('eps_surprise_pct', 'REAL'), ('revenue_surprise_pct', 'REAL'),
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
    ('guidance_valid', 'INTEGER'),
    ('sue', 'REAL'), ('hist_runup_avg', 'REAL'),
    ('seasonality_match', 'INTEGER'), ('pct_from_52w_low', 'REAL'),
    ('eps_streak', 'INTEGER'), ('revenue_streak', 'INTEGER'),
    ('vix_level', 'REAL'), ('oil_move_1d', 'REAL'),
    ('analyst_consensus', 'INTEGER'),
    ('recommendation_mean', 'REAL'),
    ('upgrade_count', 'INTEGER'),
    ('downgrade_count', 'INTEGER'),
    ('net_analyst_momentum', 'INTEGER'),
    ('has_analyst_coverage', 'INTEGER'),
    ('upward_revision_count60d', 'INTEGER'),
    ('downward_revision_count60d', 'INTEGER'),
    ('net_revision_count_60d', 'INTEGER'),
    ('revision_breadth_60d', 'REAL'),
    ('revision_trend_label', 'TEXT'),
    ('estimate_revision_pct', 'REAL'),
    ('insider_flag', 'INTEGER'), ('insider_net_value', 'REAL'),
    ('insider_buy_count', 'INTEGER'), ('insider_sell_count', 'INTEGER'),
    ('market_cap_bucket', 'TEXT'), ('log_market_cap', 'REAL'),
    ('sector', 'TEXT'), ('industry', 'TEXT'),
    ('return_20d', 'REAL'), ('return_60d', 'REAL'), ('return_120d', 'REAL'),
    ('volatility_20d', 'REAL'), ('volatility_60d', 'REAL'),
    ('sector_relative_strength', 'REAL'),
    ('stock_vs_spy_20d', 'REAL'),
    ('stock_vs_sector_20d', 'REAL'),
    ('hv20_current', 'REAL'),
    ('vol_percentile', 'REAL'),
    ('high_vol_regime', 'INTEGER'),
]

for col, col_type in columns:
    try:
        c.execute(f"ALTER TABLE ml_dataset ADD COLUMN {col} {col_type}")
    except sqlite3.OperationalError:
        pass
conn.commit()

# ---------------------------------------------------------------------------
# 2. Select a batch of rows that need features – any ticker, any date,
#    as long as it has a target (i.e., it's a past event) and is missing features.
#    Prioritise most recent events first.
# ---------------------------------------------------------------------------
df = pd.read_sql(f"""
    SELECT ticker, earnings_date FROM ml_dataset
    WHERE quality_curr IS NULL
      AND target_5d_drift IS NOT NULL
    ORDER BY earnings_date DESC
    LIMIT {BATCH_SIZE}
""", conn, parse_dates=['earnings_date'])

if df.empty:
    print("No rows left to backfill. All done!")
    conn.close()
    exit()

print(f"Processing {len(df)} historical rows...")

def safe_get(val, key=None):
    if isinstance(val, dict):
        return val.get(key) if key else None
    return val

ticker_cache = {}

for counter, (idx, row) in enumerate(df.iterrows(), 1):
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

    # ---- Compute all features ----
    curr     = current_earnings_quality(ticker, ed)
    hist     = historical_earnings_quality(ticker, ed)
    runup    = compute_runup(ticker, ed, df_price)
    rsi      = compute_rsi(ticker, ed, df_price)
    vol_rat  = compute_volume_ratio(ticker, ed, df_price)
    past     = compute_past_earnings_action(ticker, ed, df_price, ed_series)
    guidance = compute_prior_guidance_raised(ticker, ed)
    sec_rel  = compute_sector_relative_strength(ticker, ed, df_price)
    sue      = compute_sue(ticker, ed)
    hist_run = compute_historical_runup_avg(ticker, ed, df_price, ed_series)
    season   = compute_seasonality_match(ticker, ed, df_price, ed_series)
    streaks  = compute_eps_rev_streak(ticker, ed, ed_series)
    market   = get_market_context(ed)
    pct_52w  = compute_pct_from_52wlow(ticker, ed, df_price)

    mom = analyst_momentum(ticker, ed)
    consensus_proxy = None
    rec_mean = None; up_count = None; down_count = None
    net_mom = None; has_coverage = None
    if mom:
        net_mom = mom.get('net_analyst_momentum')
        if net_mom is not None:
            consensus_proxy = 1 if net_mom > 0 else 0
        rec_mean = mom.get('recommendation_mean')
        up_count = mom.get('upgrade_count')
        down_count = mom.get('downgrade_count')
        has_coverage = mom.get('has_analyst_coverage')

    rev_feats = analyst_revision(ticker, ed)
    insider   = compute_insider_transactions(ticker, ed)
    mcap_feats = compute_market_cap_features(ticker, ed, df_price)
    sect_info  = compute_sector_industry(ticker)
    mom_feats  = compute_momentum_features(ed, df_price)
    vol_feats  = compute_volatility_features(ed, df_price)
    vol_pct    = compute_volatility_percentile(ticker, ed, df_price)

    c.execute("""
        UPDATE ml_dataset SET
            quality_curr = ?, score_curr = ?, revenue_latest = ?, revenue_prev = ?,
            gm_change_bps = ?, sbc_pct_curr = ?, ocf_ni_ratio = ?, fcf_positive = ?,
            revenue_beat = ?, eps_beat_curr = ?, gaap_profit = ?,
            eps_surprise_pct = ?, revenue_surprise_pct = ?,
            hist_quality = ?, avg_gm = ?, avg_sbc = ?, avg_ocf = ?,
            fcf_pos_count = ?, yoy_growth_streak = ?,
            scs_market_punishing = ?, scs_monetisation_evidence = ?,
            scs_conviction_penalty = ?, scs_capex_trigger = ?,
            runup = ?, rsi = ?, volume_ratio = ?,
            surge_hold_count = ?, fade_count = ?, drop_count = ?,
            past_earnings_action = ?, pct_surge = ?,
            pullback_bounce_count = ?, avg_pullback_depth = ?,
            past_pullback_bounce = ?, post_earnings_drift = ?,
            guidance_valid = ?, sue = ?,
            hist_runup_avg = ?, seasonality_match = ?,
            eps_streak = ?, revenue_streak = ?,
            vix_level = ?, oil_move_1d = ?,
            pct_from_52w_low = ?,
            analyst_consensus = ?,
            recommendation_mean = ?, upgrade_count = ?, downgrade_count = ?,
            net_analyst_momentum = ?, has_analyst_coverage = ?,
            upward_revision_count60d = ?, downward_revision_count60d = ?,
            net_revision_count_60d = ?, revision_breadth_60d = ?,
            revision_trend_label = ?, estimate_revision_pct = ?,
            insider_flag = ?, insider_net_value = ?, insider_buy_count = ?, insider_sell_count = ?,
            market_cap_bucket = ?, log_market_cap = ?,
            sector = ?, industry = ?,
            return_20d = ?, return_60d = ?, return_120d = ?,
            volatility_20d = ?, volatility_60d = ?,
            sector_relative_strength = ?,
            stock_vs_spy_20d = ?, stock_vs_sector_20d = ?,
            hv20_current = ?, vol_percentile = ?, high_vol_regime = ?
        WHERE ticker = ? AND earnings_date = ?
    """, (
        safe_get(curr, 'quality'), safe_get(curr, 'score'),
        safe_get(curr, 'revenue_latest'), safe_get(curr, 'revenue_prev'),
        safe_get(curr, 'gm_change_bps'), safe_get(curr, 'sbc_pct'),
        safe_get(curr, 'ocf_ni_ratio'), safe_get(curr, 'fcf_positive'),
        safe_get(curr, 'revenue_beat'), safe_get(curr, 'eps_beat'),
        safe_get(curr, 'gaap_profit'),
        safe_get(curr, 'eps_surprise_pct'), safe_get(curr, 'revenue_surprise_pct'),
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
        safe_get(guidance), safe_get(sue),
        safe_get(hist_run), safe_get(season),
        safe_get(streaks, 'eps_streak'), safe_get(streaks, 'revenue_streak'),
        safe_get(market, 'vix_level'), safe_get(market, 'oil_move_1d'),
        safe_get(pct_52w),
        consensus_proxy,
        rec_mean, up_count, down_count,
        net_mom, has_coverage,
        safe_get(rev_feats, 'upward_revision_count60d'),
        safe_get(rev_feats, 'downward_revision_count60d'),
        safe_get(rev_feats, 'net_revision_count_60d'),
        safe_get(rev_feats, 'revision_breadth_60d'),
        safe_get(rev_feats, 'revision_trend_label'),
        safe_get(rev_feats, 'estimate_revision_pct'),
        safe_get(insider, 'insider_flag'), safe_get(insider, 'net_value'),
        safe_get(insider, 'buy_count'), safe_get(insider, 'sell_count'),
        safe_get(mcap_feats, 'market_cap_bucket'), safe_get(mcap_feats, 'log_market_cap'),
        safe_get(sect_info, 'sector'), safe_get(sect_info, 'industry'),
        safe_get(mom_feats, 'return_20d'), safe_get(mom_feats, 'return_60d'), safe_get(mom_feats, 'return_120d'),
        safe_get(vol_feats, 'volatility_20d'), safe_get(vol_feats, 'volatility_60d'),
        safe_get(sec_rel, 'sector_spy_return_ratio'),
        safe_get(sec_rel, 'stock_vs_spy_20d'), safe_get(sec_rel, 'stock_vs_sector_20d'),
        safe_get(vol_pct, 'hv20_current'), safe_get(vol_pct, 'vol_percentile'), safe_get(vol_pct, 'high_vol_regime'),
        ticker, ed.strftime('%Y-%m-%d')
    ))
    conn.commit()
    time.sleep(0.2)

print(f"Batch complete. {len(df)} rows processed.")
conn.close()