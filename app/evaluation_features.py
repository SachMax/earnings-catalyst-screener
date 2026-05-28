import sqlite3
import pandas as pd

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

# Add new columns for the scoring output if they don't already exist
for col in ['filters_passed', 'conviction', 'position_size_pct', 'phase']:
    try:
        c.execute(f"ALTER TABLE features ADD COLUMN {col} TEXT" if col == 'phase' else f"ALTER TABLE features ADD COLUMN {col} REAL")
    except sqlite3.OperationalError:
        pass

# Load all features for upcoming earnings events
df = pd.read_sql("SELECT * FROM features WHERE earnings_date > date('now')", conn, parse_dates=['earnings_date'])

# ================================================================
# 1. DEFINE FILTER MAP
# ================================================================
# Each tuple: (column name, pass condition)
# For binary columns, pass condition is == 1.
# For continuous columns, we define thresholds.
# NULL values will be treated as neutral (i.e., not counted).
filter_checks = [
    ('eps_beat', 1),                          # 1  - EPS Beat
    ('revenue_growth_YoY', 1),                # 2  - Revenue Growth YoY (proxy for beat)
    ('guidance_valid', 1),                    # 3  - Guidance Raised
    ('gaap_profit', 1),                       # 4  - GAAP Profitability
    ('recommendationMean', '>=2.0'),          # 5  - Analyst Consensus (mean rating >= 2.0 buy)
    ('net_analyst_momentum', '>0'),           # 6  - Recent Analyst Momentum positive
    ('eps_streak', '>=3'),                    # 7  - EPS Beat Streak ≥ 3
    ('revenue_growth_streak', '>=3'),         # 8  - Revenue Growth Streak ≥ 3 (proxy)
    ('sector_relative_strength', '>0'),       # 9  - Sector Tailwind
    ('valuation_pe', '<30'),                  # 11 - Valuation (P/E < 30)
    ('implied_move', '>=7.0'),                # 12 - Options‑Implied Move ≥ 7%
    ('runup', '<=2.0'),                       # 13 - Current Run‑Up ≤ 2%
    ('past_earnings_action', '==Surge & Hold'),# 14 - Past Earnings Action
    ('past_pullback_bounce', '==pullback and bounce'),# 15 - Historical Pullback & Bounce
    ('short_interest', '<=5.0'),              # 16 - Short Interest ≤ 5%
    ('insider_transactions', 1),              # 17 - Insider Net Buying (flag 1)
    ('post_earnings_drift', '>0'),            # 20 - Post‑Earnings Drift positive
    ('sue', '>=2.0'),                         # 21 - SUE ≥ 2.0
    ('net_revision_count_60d', '>0'),         # 22 - Analyst Net Revisions positive
    ('call_put_volume_ratio', '>1.5'),        # 23a - Call/Put Volume Ratio > 1.5
    ('put_call_price_skew', '<=1.5'),         # 23b - Put‑Call Price Skew ≤ 1.5
    ('iv_hv_ratio', '>1.5'),                  # 24 - IV/HV Ratio > 1.5
    ('volume_confirmation', '>=1.5'),         # 25 - Post‑Earnings Volume ≥ 1.5x
    ('rsi', '<60'),                           # 26 - RSI < 60
    ('seasonality_match', 1),                 # 28 - Seasonality Match
    ('current_earnings_quality', '>=2'),      # 19 - Current Earnings Quality ≥ Medium (score≥2)
    ('hist_earnings_quality', '>=2'),         # 19 - Historical Quality ≥ Medium
    ('scs_conviction_penalty', '==None'),     # 30 - No Capex Sentiment Penalty (None or 'None')
]

def check_filter(row, col, condition):
    """Return True if the filter passes, False if it fails, None if data missing."""
    val = row.get(col)
    if val is None or pd.isna(val):
        return None
    if isinstance(condition, int):          
        return val == condition
    if isinstance(condition, str):          
        try:
            if condition.startswith('=='):
                return str(val) == condition[2:].strip()
            elif condition.startswith('>='):
                return float(val) >= float(condition[2:])
            elif condition.startswith('<='):
                return float(val) <= float(condition[2:])
            elif condition.startswith('>'):
                return float(val) > float(condition[1:])
            elif condition.startswith('<'):
                return float(val) < float(condition[1:])
            elif condition.startswith('!='):
                return float(val) != float(condition[2:])
        except:
            return None
    return None

# ================================================================
# 2. EVALUATE EACH TICKER
# ================================================================
for idx, row in df.iterrows():
    ticker = row['ticker']
    ed = row['earnings_date'].strftime('%Y-%m-%d')
    print(f"\n{ticker} raw guidance_valid = {row.get('guidance_valid')}, type={type(row.get('guidance_valid'))}")
    # -------- Trifecta Gate --------
    trifecta_pass = True
    for gate_col in ['eps_beat', 'guidance_valid', 'gaap_profit']:
        val = row.get(gate_col)
        if val is None or (isinstance(val, float) and pd.isna(val)) or val == 0:
            trifecta_pass = False
            break

    # Phase 2 eligibility requires all three Trifecta filters to pass.
    # Phase 4 requires only that the earnings are out (implicitly we assume post‑earnings).
    # We'll assign Phase 2 if Trifecta passes, else Phase 4 if we have some other signal (like pullback).
    # For simplicity, first draft: Trifecta pass -> Phase 2 candidate, else Phase 4 if there is a
    # past earnings date (i.e., we're looking at post‑earnings setup). We'll refine later.
    # We'll also check for Phase 5 conditions (but that's complex, leave for now).

    # Count passed filters
    passed_count = 0
    total_available = 0
    for col, cond in filter_checks:
        res = check_filter(row, col, cond)
        if res is True:
            passed_count += 1
        if res is not None:
            total_available += 1

    # Determine conviction from passed count (v2.9 table)
    # The v2.9 conviction thresholds:
    # ≥22: Very High, 18-21: High, 14-17: Medium, <14: Low
    if passed_count >= 22:
        conviction = 'Very High'
        size_pct = 2.5
    elif passed_count >= 18:
        conviction = 'High'
        size_pct = 2.0
    elif passed_count >= 14:
        conviction = 'Medium'
        size_pct = 1.5
    elif passed_count >= 9:
        conviction = 'Low'
        size_pct = 0.5
    else:
        conviction = 'None'
        size_pct = 0.0

    # Assign phase (simplified first draft)
    if trifecta_pass and passed_count >= 14:
        phase = 'Phase 2'
    elif not trifecta_pass and passed_count >= 9:
        # post‑earnings opportunity
        phase = 'Phase 4'
    else:
        phase = 'Skip'

    # Write results
    c.execute("UPDATE features SET filters_passed=?, conviction=?, position_size_pct=?, phase=? WHERE ticker=? AND earnings_date=?",
              (passed_count, conviction, size_pct, phase, ticker, ed))
    print(f"{ticker}: Trifecta={'OK' if trifecta_pass else 'No'}, Passed={passed_count}/{total_available}, conviction = {conviction}, {phase}")

conn.commit()
conn.close()