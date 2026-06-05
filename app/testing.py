# test_features_on_date.py
import pandas as pd
from datetime import date
from features_library import *

TICKER = "MSFT"
TEST_DATE = date(2019, 7, 15)

print(f"Testing all features on {TICKER} as of {TEST_DATE}\n")

# 1. Data loaders
df_price = load_price_history(TICKER)
ed_series = load_earnings_dates(TICKER)
print("✅ Data loaders OK")

# 2. Current earnings quality
curr = current_earnings_quality(TICKER, TEST_DATE)
if curr:
    print(f"✅ current_earnings_quality -> quality={curr['quality']}, eps_beat={curr['eps_beat']}")
else:
    print("❌ current_earnings_quality returned None")

# 3. Historical earnings quality
hist = historical_earnings_quality(TICKER, TEST_DATE)
if hist:
    print(f"✅ historical_earnings_quality -> quality={hist['quality']}, scs_penalty={hist['scs_conviction_penalty']}")
else:
    print("❌ historical_earnings_quality returned None")

# 4. Analyst functions
cons = analyst_consensus(TICKER, TEST_DATE)
print(f"✅ analyst_consensus -> {cons}")

mom = analyst_momentum(TICKER, TEST_DATE)
if mom:
    print(f"✅ analyst_momentum -> net={mom['net_analyst_momentum']}")
else:
    print("❌ analyst_momentum returned None")

rev = analyst_revision(TICKER, TEST_DATE)
if rev:
    print(f"✅ analyst_revision -> trend={rev['revision_trend_label']}")
else:
    print("❌ analyst_revision returned None")

# 5. Price‑based features
runup = compute_runup(TICKER, TEST_DATE, df_price)
print(f"✅ runup -> {runup}")

rsi = compute_rsi(TICKER, TEST_DATE, df_price)
print(f"✅ rsi -> {rsi}")

vol_rat = compute_volume_ratio(TICKER, TEST_DATE, df_price)
print(f"✅ volume_ratio -> {vol_rat}")

# 6. Past earnings features
past = compute_past_earnings_action(TICKER, TEST_DATE, df_price, ed_series)
if past:
    print(f"✅ past_earnings_action -> action={past['past_earnings_action']}, drift={past['post_earnings_drift']}")
else:
    print("❌ past_earnings_action returned None")

# 7. Guidance, sector, SUE, market context
guidance = compute_guidance_valid(TICKER, TEST_DATE)
print(f"✅ guidance -> {guidance}")

sec_rel = compute_sector_relative_strength(TICKER, TEST_DATE)
print(f"✅ sector_relative_strength -> {sec_rel}")

sue = compute_sue(TICKER, TEST_DATE)
print(f"✅ sue -> {sue}")

hist_runup = compute_historical_runup_avg(TICKER, TEST_DATE, df_price, ed_series)
print(f"✅ hist_runup_avg -> {hist_runup}")

season = compute_seasonality_match(TICKER, TEST_DATE, df_price, ed_series)
print(f"✅ seasonality_match -> {season}")

streaks = compute_eps_rev_streak(TICKER, TEST_DATE, ed_series)
if streaks:
    print(f"✅ eps_rev_streak -> eps={streaks['eps_streak']}, rev={streaks['revenue_streak']}")
else:
    print("❌ eps_rev_streak returned None")

market = get_market_context(TEST_DATE)
if market:
    print(f"✅ market_context -> VIX={market['vix_level']}, oil={market['oil_move_1d']}")
else:
    print("❌ market_context returned None")

pct_52w = compute_pct_from_52wlow(TICKER, TEST_DATE, df_price)
print(f"✅ 52‑week position -> {pct_52w}")

# 8. Insider (optional – can skip if too slow)
# insider = compute_insider_transactions(TICKER, TEST_DATE)
# print(f"✅ insider -> {insider}")

print("\n🏁 All tests completed.")