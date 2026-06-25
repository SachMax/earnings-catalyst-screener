# evaluation_features.py
import sqlite3
import pandas as pd
from datetime import date

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

# ---------------------------------------------------------------------------
# 0. Ensure evaluation output columns exist
# ---------------------------------------------------------------------------
for col in ['filters_passed', 'conviction', 'position_size_pct', 'phase']:
    try:
        c.execute(f"ALTER TABLE features ADD COLUMN {col} TEXT" if col == 'phase'
                  else f"ALTER TABLE features ADD COLUMN {col} REAL")
    except sqlite3.OperationalError:
        pass

# ---------------------------------------------------------------------------
# 1. Load upcoming events (next 7 days for live screening)
# ---------------------------------------------------------------------------
today = date.today().strftime('%Y-%m-%d')
df = pd.read_sql(f"SELECT * FROM features WHERE earnings_date > date('now')",
                 conn, parse_dates=['earnings_date'])

if df.empty:
    print("No upcoming earnings found.")
    conn.close()
    exit()

# ================================================================
# 2. FILTER DEFINITIONS (v2.10 order, correct column names)
# ================================================================
# Each tuple: (filter_number, column_name, pass_condition)
# condition: integer for equality, string for comparison
# None for filters that need custom handling or are qualitative

filter_checks = [
    # Trifecta Core (1‑4)
    (1,  'eps_beat',                  1),
    (2,  'revenue_beat',              1),
    (3,  'guidance_finbert_prob',     '>=0.5'),    # 🆕 FinBERT guidance
    (4,  'gaap_clean',                1),

    # Fundamental (5‑11)
    (5,  'recommendationMean',        '>=2.0'),
    (6,  'net_analyst_momentum',      '>0'),
    (7,  'eps_streak',                '>=3'),
    (8,  'revenue_growth_streak',     '>=3'),
    (9,  'sector_relative_strength',  '>0'),       # Sector ETF vs SPY
    (10, None, None),                              # Blemish – qualitative
    (11, 'valuation_pe',              '<30'),

    # Technical (12‑15)
    (12, 'implied_move',              '>=7.0'),
    (13, 'runup',                     '<=5.0'),
    (14, 'pct_surge_hold',            '>=0.5'),
    (15, 'pullback_bounce_count',     '>=3'),

    # Market & Sentiment (16‑21)
    (16, 'short_interest',            '<=5.0'),
    (17, 'insider_transactions',      1),
    (18, None, None),                              # Whisper – unavailable
    (19, 'hist_earnings_quality',     '>=2'),
    (20, 'post_earnings_drift',       '>0'),
    (21, None, None),                              # SCS – handled separately

    # Advanced Quant & Technical (22‑30)
    (22, 'sue',                       '>=2.0'),
    (23, 'net_revision_count_60d',    '>0'),
    (24, None, None),                              # Options Sentiment – custom
    (25, 'iv_hv_ratio',               '>1.5'),
    (26, 'volume_confirmation',       '>=1.5'),
    (27, 'rsi',                       '<60'),
    (28, 'seasonality_match',         1),

    # 🆕 Stock‑relative strength filters
    (29, 'stock_vs_spy_20d',          '>0'),       # Stock outperforming SPY
    (30, 'stock_vs_sector_20d',       '>0'),       # Stock outperforming its own sector ETF
]

def check_filter(row, col, condition):
    """Return True if filter passes, False if fails, None if data missing."""
    if col is None or condition is None:
        return None
    val = row.get(col)
    if val is None or (isinstance(val, float) and pd.isna(val)):
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
# 3. EVALUATE EACH TICKER
# ================================================================
for idx, row in df.iterrows():
    ticker = row['ticker']
    ed = row['earnings_date'].strftime('%Y-%m-%d')

    # -------- Trifecta Gate (v2.10) --------
    trifecta_pass = True
    for gate_col, gate_cond in [('eps_beat', 1), ('revenue_beat', 1),
                                ('guidance_finbert_prob', '>=0.5'), ('gaap_clean', 1)]:
        val = row.get(gate_col)
        if gate_cond == '>=0.5':
            if val is None or (isinstance(val, float) and pd.isna(val)) or val < 0.5:
                trifecta_pass = False
                break
        else:
            if val is None or (isinstance(val, float) and pd.isna(val)) or val == 0:
                trifecta_pass = False
                break

    # -------- Count passed filters --------
    passed_count = 0
    total_available = 0

    for num, col, cond in filter_checks:
        res = check_filter(row, col, cond)
        if res is True:
            passed_count += 1
        if res is not None:
            total_available += 1

    # -------- Custom Filter 21 (SCS) --------
    scs_pass = None
    scs_penalty = False
    scs_col = 'scs_conviction_penalty'
    if scs_col in row.index:
        penalty = row[scs_col]
        if pd.isna(penalty) or penalty is None or penalty == 'None':
            scs_pass = True
        elif penalty == 'Reduce':
            scs_pass = True
            scs_penalty = True
        elif penalty == 'Skip':
            scs_pass = False
        if scs_pass is not None:
            total_available += 1
            if scs_pass:
                passed_count += 1

    # -------- Custom Filter 24 (Options Sentiment) --------
    skew_penalty = False
    opt_pass = None

    call_ratio = row.get('call_put_volume_ratio')
    put_skew   = row.get('put_call_price_skew')

    if put_skew is not None and not pd.isna(put_skew):
        if put_skew > 2.0:
            opt_pass = False
        elif put_skew > 1.5:
            opt_pass = True
            skew_penalty = True
        else:   # put_skew <= 1.5
            opt_pass = True
    elif call_ratio is not None and not pd.isna(call_ratio):
        # fallback: call/put volume ratio > 1.5 is bullish
        if call_ratio > 1.5:
            opt_pass = True
        # else not enough info → opt_pass stays None
    # if both missing, opt_pass stays None

    if opt_pass is not None:
        total_available += 1
        if opt_pass:
            passed_count += 1

    # -------- Conviction & Base Size (v2.10) --------
    if passed_count >= 22:
        conviction = 'Very High'
        base_size = 4.5
    elif passed_count >= 18:
        conviction = 'High'
        base_size = 3.0
    elif passed_count >= 14:
        conviction = 'Medium'
        base_size = 1.5
    else:
        conviction = 'Low'
        base_size = 0.0

    # -------- Conviction Penalties (tier reduction) --------
    tier_reduce = {
        'Very High': 'High',
        'High': 'Medium',
        'Medium': 'Low',
        'Low': 'Low'
    }
    if skew_penalty:
        conviction = tier_reduce.get(conviction, 'Low')
        base_size *= 0.5
    if scs_penalty:
        conviction = tier_reduce.get(conviction, 'Low')
        base_size *= 0.5

    # -------- Phase 2 only (Pre‑earnings dip) --------
    if trifecta_pass and conviction != 'Low' and base_size > 0:
        phase = 'Phase 2'
    else:
        phase = 'Skip'
        base_size = 0.0

    # -------- Run‑Up Adjustment (Filter 13) --------
    runup_val = row.get('runup')
    if runup_val is not None and not pd.isna(runup_val):
        if runup_val > 5.0:
            phase = 'Skip'
            base_size = 0.0
        elif runup_val > 3.0:
            base_size *= 0.5
        elif runup_val < 1.0:
            base_size *= 1.5
            max_map = {'Very High': 6.0, 'High': 4.0, 'Medium': 2.0}
            if conviction in max_map:
                base_size = min(base_size, max_map[conviction])

    # -------- Market Context (Elevated risk) --------
    vix = row.get('vix_level')
    oil = row.get('oil_move_1d')
    elevated = False
    if vix is not None and not pd.isna(vix) and 20 <= vix < 25:
        elevated = True
    if oil is not None and not pd.isna(oil) and oil > 3.0:
        elevated = True

    if elevated:
        base_size *= 0.5

    # -------- Write to database --------
    c.execute("""
        UPDATE features SET
            filters_passed = ?,
            conviction = ?,
            position_size_pct = ?,
            phase = ?
        WHERE ticker = ? AND earnings_date = ?
    """, (passed_count, conviction, round(base_size, 2), phase, ticker, ed))

    print(f"{ticker}: Trifecta={'OK' if trifecta_pass else 'No'}, "
          f"Passed={passed_count}/{total_available}, "
          f"Conviction={conviction}, Phase={phase}, Size={base_size:.2f}%")

conn.commit()
conn.close()
print("\nEvaluation complete.")