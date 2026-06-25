# init_features_table.py
import sqlite3

DB_PATH = 'data/universe.db'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# ---------------------------------------------------------------------------
# 1. Create the features table if it doesn't exist (with ALL columns)
# ---------------------------------------------------------------------------
c.execute("""
CREATE TABLE IF NOT EXISTS features (
    ticker TEXT,
    earnings_date TEXT,

    -- Trifecta Core (Filters 1 to 4)
    eps_beat INTEGER,
    revenue_growth_YoY INTEGER,
    revenue_growth_streak INTEGER,
    revenue_beat INTEGER,
    guidance_valid INTEGER,
    guidance_finbert_prob REAL,
    gaap_profit INTEGER,
    sbc_pct_revenue REAL,
    gaap_clean INTEGER,

    -- Fundamental (Filters 5 to 11)
    recommendationKey TEXT,
    recommendationMean REAL,
    analyst_upgrades INTEGER,
    analyst_downgrades INTEGER,
    net_analyst_momentum INTEGER,
    eps_streak INTEGER,
    revenue_beat_streak INTEGER,
    sector TEXT,
    sector_relative_strength REAL,
    valuation_pe REAL,
    peg_ratio REAL,
    pct_from_52w_low REAL,

    -- Technical (Filters 12 to 16)
    implied_move REAL,
    runup REAL,
    hist_runup_avg REAL,
    past_earnings_action TEXT,
    surge_hold_count INTEGER,
    fade_count INTEGER,
    drop_count INTEGER,
    pct_surge_hold REAL,
    past_pullback_bounce TEXT,
    pullback_bounce_count INTEGER,
    avg_pullback_depth REAL,
    rsi REAL,
    volume_confirmation REAL,
    short_interest REAL,

    -- Market & Sentiment (Filters 17 to 21, 30)
    insider_transactions INTEGER,
    insider_net_value REAL,
    insider_buy_count INTEGER,
    insider_sell_count INTEGER,
    post_earnings_drift REAL,
    sue REAL,
    seasonality_match INTEGER,

    -- Analyst Revision (Filter 22)
    upward_revision_count_60d INTEGER,
    downward_revision_count_60d INTEGER,
    net_revision_count_60d INTEGER,
    revision_breadth_60d REAL,
    revision_trend_label TEXT,
    estimate_revision_pct REAL,

    -- Options Sentiment (Filter 23)
    call_put_volume_ratio REAL,
    put_call_price_skew REAL,

    -- Volatility (Filter 24)
    iv_hv_ratio REAL,

    -- Earnings Quality (Filter 19): current & historical
    current_gm_change_bps REAL,
    current_sbc_pct REAL,
    current_ocf_ni_ratio REAL,
    current_fcf_positive INTEGER,
    current_earnings_quality INTEGER,
    hist_gm_change_avg REAL,
    hist_sbc_pct_avg REAL,
    hist_ocf_ni_avg REAL,
    hist_fcf_quarters INTEGER,
    hist_earnings_quality INTEGER,

    -- Capex Sentiment (Filter 30): tech only
    scs_market_punishing_capex INTEGER,
    scs_monetisation_evidence INTEGER,
    scs_conviction_penalty TEXT,
    scs_capex_trigger_active INTEGER,

    -- Evaluation output (written by evaluation_features.py)
    filters_passed REAL,
    conviction TEXT,
    position_size_pct REAL,
    phase TEXT,

    -- New columns (from ml_dataset / features_remaining_update)
    market_cap_bucket TEXT,
    log_market_cap REAL,
    return_20d REAL,
    return_60d REAL,
    return_120d REAL,
    volatility_20d REAL,
    volatility_60d REAL,
    stock_vs_spy_20d REAL,
    stock_vs_sector_20d REAL,
    hv20_current REAL,
    vol_percentile REAL,
    high_vol_regime INTEGER,
    vix_level REAL,
    oil_move_1d REAL,
    volume_ratio REAL,

    PRIMARY KEY (ticker, earnings_date)
)
""")

# ---------------------------------------------------------------------------
# 2. Idempotent safety net – add any new columns if the table already existed
# ---------------------------------------------------------------------------
new_columns = [
    ('market_cap_bucket', 'TEXT'),
    ('log_market_cap', 'REAL'),
    ('return_20d', 'REAL'),
    ('return_60d', 'REAL'),
    ('return_120d', 'REAL'),
    ('volatility_20d', 'REAL'),
    ('volatility_60d', 'REAL'),
    ('stock_vs_spy_20d', 'REAL'),
    ('stock_vs_sector_20d', 'REAL'),
    ('hv20_current', 'REAL'),
    ('vol_percentile', 'REAL'),
    ('high_vol_regime', 'INTEGER'),
    ('vix_level', 'REAL'),
    ('oil_move_1d', 'REAL'),
    ('volume_ratio', 'REAL'),
    ('guidance_finbert_prob', 'REAL')
]

for col_name, col_type in new_columns:
    try:
        c.execute(f"ALTER TABLE features ADD COLUMN {col_name} {col_type}")
    except sqlite3.OperationalError:
        pass   # column already exists

conn.commit()
conn.close()
print("features table initialised with all columns.")