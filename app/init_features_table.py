import sqlite3

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS features (
    ticker TEXT,
    earnings_date TEXT,

    -- Trifecta Core (Filters 1 to 4)
    eps_beat INTEGER,
    revenue_growth_YoY INTEGER, 
    revenue_growth_streak INTEGER,
    revenue_beat INTEGER,                      -- Filter 2 (to be added soon)
    guidance_valid INTEGER,                     
    gaap_profit INTEGER,
    sbc_pct_revenue REAL,
    gaap_clean INTEGER,                          -- derived: gaap_profit AND sbc<3%

    -- Fundamental (Filters 5 to 11)
    recommendationKey TEXT,
    recommendationMean REAL,
    analyst_upgrades INTEGER,
    analyst_downgrades INTEGER,
    net_analyst_momentum INTEGER,
    eps_streak INTEGER,
    revenue_beat_streak INTEGER,                 -- Filter 8 (to be added soon)
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

    PRIMARY KEY (ticker, earnings_date)
)
""")
conn.commit()
conn.close()