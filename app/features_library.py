# POINT-IN-TIME CAUTION: EDGAR financial facts selected by quarter end may
# include figures filed after a historical cutoff. Do not treat this
# entire library as leakage-free without filing-availability checks.

# NAME of functions
# 1. eps_beat(ticker, as_of_date): returns 0, 1, None INTEGER (eps_beat from current earnings quality func)
# 2. analyst_consensus(ticker, as_of_date): returns consesus_proxy TEXT
# 3. analyst_momentum(ticker, as_of_date): returns a dictionary 'recommendation_mean', 'upgrade_count', 'downgrade_count', 'net_analyst_momentum'
# 4. analyst_revision(ticker, as_of_date): returns a dictionaty 'upward_revision_count60d', 'downward_revision_count60d', 'net_revision_count_60d','revision_breadth_60d', 'revision_trend_label', 'estimate_revision_pct'
# 5. historical_earnings_quality(ticker, as_of_date):
# returns {
#         'quality': hist_score,
#         'avg_gm': avg_gm,
#         'avg_sbc': avg_sbc,
#         'avg_ocf': avg_ocf,
#         'fcf_pos_count': fcf_pos_count,
#         'yoy_growth_streak': yoy_growth_streak,
#         'scs_market_punishing_capex': market_punishing,
#         'scs_monetisation_evidence': monetisation_latest,
#         'scs_conviction_penalty': conviction_penalty,
#         'scs_capex_trigger_active': capex_trigger
#     }
# 6. current_earnings_quality(ticker, as_of_date): 
# returns {
#     'quality': quality,
#     'score': score,
#     'revenue_latest': revenue_latest,
#     'revenue_prev': revenue_prev,
#     'gm_change_bps': gm_change_bps,
#     'sbc_pct': sbc_pct,
#     'ocf_ni_ratio': ocf_ni_ratio,
#     'fcf_positive': fcf_positive,
#     'revenue_beat': revenue_beat,
#     'eps_beat': eps_beat,
#     'gaap_profit': gaap_profit
# }
# 7. load_price_history(ticker): returns df_price
# 8. compute_runup(ticker, as_of_date, df_price): returns run up
# 9. compute_rsi(ticker, as_of_date, df_price): returns rsi
# 10. compute_volume_ratio(ticker, as_of_date, df_price): returns post_volume/pre_volume ratio
# 11. load_earnings_dates(ticker): returns df_ed_history
# 12. compute_past_earnings_action(ticker, as_of_date, df_price, df_ed):
# returns {
#     'surge_hold_count': surge_count,
#     'fade_count': fade_count,
#     'drop_count': drop_count,
#     'past_earnings_action': most_common_action,
#     'pct_surge': pct_surge,
#     'pullback_bounce_count': pb_count,
#     'avg_pullback_depth': avg_depth,
#     'past_pullback_bounce': most_common_reaction,
#     'post_earnings_drift': avg_drift
# }
# 13. compute_guidance_valid(ticker, as_of_date): returns guidance confirmation
# 14. compute_sector_relative_strength(ticker, as_of_date): returns sector relative strength
# 15. compute_sue(ticker, as_of_date): returns SUE
# 16. compute_historical_runup_avg(ticker, as_of_date, df_price, ed_series): returns hist run up avg
# 17. compute_seasonality_match(ticker, as_of_date, df_price, ed_series): returns seasonality match confirmation (0/1)
# 18. compute_insider_transactions(ticker, as_of_date, max_filings=50):
# returns {
#      'insider_flag': insider_flag,
#      'net_value': round(net_value, 2),
#      'buy_count': buy_count,
#      'sell_count': sell_count
# }
# 19. compute_eps_rev_streak(ticker, as_of_date, ed_series):
# returns {
#     'revenue_streak': rev_streak,
#     'eps_streak': eps_streak
# }
# 20. get_market_context(as_of_date):
# returns {
#     'vix_level': vix_level, 
#     'oil_move_1d': oil_move
# }
# 21. compute_pct_from_52wlow(ticker, as_of_date, df_price): returns pct from 52 weeks low

import yfinance as yf
import sqlite3
import pandas as pd
from datetime import date, timedelta
import numpy as np
import edgar
import joblib 
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch


from pathlib import Path


def _feature_database_path():
    """Find the existing DB relative to this source file or project CWD."""
    here = Path(__file__).resolve().parent
    candidates = [Path.cwd() / 'data' / 'universe.db'] + [
        directory / 'data' / 'universe.db'
        for directory in (here, *here.parents)
    ]
    for path in candidates:
        if path.is_file():
            return str(path)
    raise FileNotFoundError('Cannot locate data/universe.db; start from project root')


_GUIDANCE_MODEL_CACHE = None

def _get_guidance_model():
    global _GUIDANCE_MODEL_CACHE
    if _GUIDANCE_MODEL_CACHE is None:
        # Resolve the saved model paths from project working directory.
        tok = AutoTokenizer.from_pretrained('./artifacts/my_guidance_tokenizer')
        net = AutoModelForSequenceClassification.from_pretrained('./artifacts/my_guidance_model')
        net.eval()
        _GUIDANCE_MODEL_CACHE = (tok, net)
    return _GUIDANCE_MODEL_CACHE

edgar.set_identity("sachiomaximilliano166@gmail.com")

# FinBERT loads lazily only if compute_guidance_bert is called.

def analyst_momentum(ticker, as_of_date):
    """Historical rating-action momentum. Do not insert today's recommendationMean."""
    result = {
        'recommendation_mean': None,  # no historical consensus snapshot available
        'upgrade_count': None,
        'downgrade_count': None,
        'net_analyst_momentum': None,
        'has_analyst_coverage': None,
    }
    try:
        ratings = yf.Ticker(ticker).upgrades_downgrades
        if ratings is None:
            return result
        if ratings.empty:
            return {**result, 'upgrade_count': 0, 'downgrade_count': 0,
                    'net_analyst_momentum': 0, 'has_analyst_coverage': 0}
        ratings = ratings.copy()
        if not isinstance(ratings.index, pd.DatetimeIndex):
            col = next((c for c in ('date', 'Date', 'filing_date', 'Filing Date')
                        if c in ratings.columns), None)
            if col is None:
                return result
            ratings.index = pd.to_datetime(ratings[col], errors='coerce', utc=True)
        else:
            ratings.index = pd.to_datetime(ratings.index, utc=True)
        cutoff = pd.Timestamp(as_of_date).tz_localize('UTC') if pd.Timestamp(as_of_date).tzinfo is None else pd.Timestamp(as_of_date).tz_convert('UTC')
        historical = ratings[ratings.index < cutoff]
        window = historical[historical.index >= cutoff - pd.Timedelta(days=14)]
        def tier(s):
            s = str(s).strip().lower()
            if s in ('buy', 'overweight', 'outperform', 'strong buy'): return 2
            if s in ('hold', 'neutral', 'market perform', 'sector perform', 'equal-weight'): return 1
            if s in ('sell', 'underperform', 'underweight', 'strong sell'): return 0
            return None
        up = down = 0
        for _, r in window.iterrows():
            before, after = tier(r.get('FromGrade')), tier(r.get('ToGrade'))
            if before is None or after is None:
                continue
            up += after > before
            down += after < before
        return {'recommendation_mean': None,
                'upgrade_count': int(up), 'downgrade_count': int(down),
                'net_analyst_momentum': int(up - down),
                'has_analyst_coverage': int(not historical.empty)}
    except Exception as exc:
        print(f'analyst_momentum({ticker}, {as_of_date}): {exc}')
        return result

def analyst_consensus(ticker, as_of_date):
    """Unavailable without point-in-time consensus data; not a rating-action proxy."""
    return None


def analyst_revision(ticker, as_of_date):
    """Historical revisions to an EPS estimate need point-in-time estimate snapshots.

    yfinance.upgrades_downgrades provides analyst rating changes, NOT
    revisions to the same quarter's EPS or revenue consensus. These rating
    changes are tracked separately by analyst_momentum(). Returning None
    here prevents mislabeled historical training features.
    """
    return {
        'upward_revision_count60d': None,
        'downward_revision_count60d': None,
        'net_revision_count_60d': None,
        'revision_breadth_60d': None,
        'revision_trend_label': None,
        'estimate_revision_pct': None,
    }

def historical_earnings_quality(ticker, as_of_date):
    """
    Compute historical earnings quality and capex sentiment for a single ticker as of a specific date.
    Returns a dict with quality, hist_score, avg_gm, avg_sbc, avg_ocf, fcf_pos_count,
    yoy_growth_streak, and SCS fields.  Non‑Tech stocks get SCS = None.
    """
    def last_day_of_month(year, month):
        days = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if month == 2 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
            return 29
        return days[month]

    def quarter_end_from_fye(label, fye_str):
        try:
            q = int(label[1])
            fy = int(label.split()[1])
            fye_month = int(fye_str[:2])
            fye_day   = int(fye_str[2:4])
        except:
            return None
        if q == 4:
            return date(fy, fye_month, fye_day)
        months_back = 3 * (4 - q)
        month = fye_month - months_back
        year = fy
        while month <= 0:
            month += 12
            year -= 1
        max_day = last_day_of_month(year, month)
        day = min(fye_day, max_day)
        return date(year, month, day)

    def get_value(df, label, quarter):
        try:
            row = df[df['label'] == label]
            if not row.empty:
                return row[quarter].iloc[0]
        except:
            pass
        return None

    # ---------- 1. Fetch financial statements from EDGAR ----------
    try:
        company = edgar.Company(ticker)
        facts = company.get_facts()
        income_df = facts.income_statement(periods=1000, annual=False, as_dataframe=True)
        cashflow_df = facts.cashflow_statement(periods=1000, annual=False, as_dataframe=True)
        fye_str = company.fiscal_year_end
        stock = yf.Ticker(ticker)
    except:
        return None

    sector = None
    try:
        stock = yf.Ticker(ticker)
        sector = stock.info.get('sector', None)
    except Exception:
        pass 

    meta_cols = {'label', 'depth', 'is_abstract', 'is_total', 'section', 'confidence'}

    def safe_quarter(col):
        if col in meta_cols:
            return None
        q_end = quarter_end_from_fye(col, fye_str)
        if q_end is None or q_end > as_of_date:
            return None
        return q_end

    income_col_info = [(col, safe_quarter(col)) for col in income_df.columns]
    income_col_info = [x for x in income_col_info if x[1] is not None]
    income_col_info.sort(key=lambda x: x[1], reverse=True)
    date_cols = [col for col, _ in income_col_info]

    cashflow_col_info = [(col, safe_quarter(col)) for col in cashflow_df.columns]
    cashflow_col_info = [x for x in cashflow_col_info if x[1] is not None]
    cashflow_col_info.sort(key=lambda x: x[1], reverse=True)
    cf_date_cols = [col for col, _ in cashflow_col_info]

    if len(date_cols) < 9:
        print(f"{ticker}: not enough quarterly columns (need at least 8), skipping")
        return None

    # ---------- 2. Compute earnings quality over four quarters ----------
    gm_changes = []
    sbc_pcts = []
    ocf_nis = []
    fcf_pos_quarters = 0
    fcf_observed_quarters = 0
    yoy_growth_streak = 0
    streak_alive = True

    # variables to capture latest quarter's monetisation
    monetisation_latest = 0
    rev_growth_latest = None

    quarterly_scores = []
    for i in range(4):
        try:
            q_col = date_cols[i]
            prev_year_col = date_cols[i + 4]
            cf_q_col = cf_date_cols[i] if i < len(cf_date_cols) else q_col
        except IndexError:
            quarterly_scores.append(2)
            continue

        # Revenue
        revenue_labels = [
            'Total Revenue', 'RevenueFromContractWithCustomerExcludingAssessedTax',
            'Revenues', 'Total net revenues', 'Total non-interest revenues',
            'Total interest income', 'Total revenues', 'Revenue from contracts with customers'
        ]
        revenue_latest = None
        revenue_prev = None
        for lbl in revenue_labels:
            val = get_value(income_df, lbl, q_col)
            if val is not None and pd.notna(val):
                revenue_latest = val
                revenue_prev = get_value(income_df, lbl, prev_year_col)
                if revenue_prev is None or pd.isna(revenue_prev):
                    revenue_prev = None
                break
        if revenue_latest is None:
            quarterly_scores.append(2)
            continue

        # Cost of revenue
        cost_of_rev_lbl = ['Cost of Revenue', 'CostOfGoodsAndServicesSold', 'CostOfRevenue']
        cost_of_rev_latest = None
        cost_of_rev_prev = None
        for m in cost_of_rev_lbl:
            val = get_value(income_df, m, q_col)
            if val is not None and pd.notna(val):
                cost_of_rev_latest = val
                cost_of_rev_prev = get_value(income_df, m, prev_year_col)
                if cost_of_rev_prev is None or pd.isna(cost_of_rev_prev):
                    cost_of_rev_prev = None
                break

        # Net income
        ni_lbl = ['Net Income (Loss) Attributable to Parent', 'NetIncomeLoss']
        ni = None
        for j in ni_lbl:
            val = get_value(income_df, j, q_col)
            if val is not None and pd.notna(val):
                ni = val
                break

        # Operating cash flow
        ocf_lbl = [
            "Net Cash Provided by (Used in) Operating Activities",
            "Net cash (used in) operating activities",
            "Operating Cash Flow",
            'NetCashProvidedByUsedInOperatingActivities'
        ]
        ocf = None
        for k in ocf_lbl:
            val = get_value(cashflow_df, k, cf_q_col)
            if val is not None and pd.notna(val):
                ocf = val
                break

        # Stock-based compensation
        sbc_q = None
        for lbl in ["ShareBasedCompensation",
                    "Share-based Payment Arrangement, Noncash Expense",
                    "Share-based Payment Arrangement, Expensed and Capitalized, Amount",
                    "Stock Based Compensation"]:
            try:
                raw1 = cashflow_df.loc[lbl, cf_q_col]
                if raw1 is not None:
                    sbc_q = raw1.item() if hasattr(raw1, 'item') else raw1
                    break
            except (KeyError, IndexError):
                continue

        # Capital expenditure
        capex = None
        for lbl in ["Capital Expenditure", "Capital Expenditures",
                    "Payments to Acquire Property, Plant, and Equipment",
                    "PaymentsToAcquirePropertyPlantAndEquipment",
                    "CapitalExpendituresIncurredButNotYetPaid"]:
            try:
                val = cashflow_df.loc[lbl, cf_q_col]
                if val is not None:
                    capex = val.item() if hasattr(val, 'item') else val
                    break
            except (KeyError, IndexError):
                continue

        # ---- Monetisation for the most recent quarter (i=0) ----
        if i == 0:
            if revenue_latest is not None and revenue_prev is not None and revenue_prev > 0:
                rev_growth_latest = (revenue_latest - revenue_prev) / revenue_prev
            else:
                rev_growth_latest = None

            monetisation_latest = 0
            if rev_growth_latest is not None and rev_growth_latest > 0.20:
                monetisation_latest = 1
            elif capex is not None and revenue_latest is not None and revenue_latest > 0:
                if (abs(capex) / revenue_latest) < 0.05:
                    monetisation_latest = 1

        # ---- YoY growth streak ----
        if streak_alive:
            if revenue_latest is not None and revenue_prev is not None and revenue_prev > 0:
                if revenue_latest > revenue_prev:
                    yoy_growth_streak += 1
                else:
                    streak_alive = False
            else:
                streak_alive = False

        # ---- Component scoring ----
        components = []
        # Gross margin
        if (all(v is not None and pd.notna(v) for v in
                [revenue_latest, cost_of_rev_latest, revenue_prev, cost_of_rev_prev])
                and revenue_latest > 0 and revenue_prev > 0):
            gm_latest = ((revenue_latest - cost_of_rev_latest) / revenue_latest) * 100
            gm_prev = ((revenue_prev - cost_of_rev_prev) / revenue_prev) * 100
            gm_change = round((gm_latest - gm_prev) * 100, 2)  # basis points
            gm_changes.append(gm_change)
            if gm_change >= 100: components.append(3)
            elif gm_change >= 0: components.append(2)
            else: components.append(1)
        else:
            components.append(2)

        # SBC %
        if sbc_q is not None and revenue_latest is not None and revenue_latest > 0:
            sbc_pct = round((sbc_q / revenue_latest) * 100, 2)
            sbc_pcts.append(sbc_pct)
            if sbc_pct < 1.5: components.append(3)
            elif sbc_pct < 3: components.append(2)
            else: components.append(1)
        else:
            components.append(2)

        # OCF / NI
        if ocf is not None and ni is not None and ni != 0:
            ocf_ni = round(ocf / ni, 2)
            ocf_ni = max(-5.0, min(5.0, ocf_ni))
            ocf_nis.append(ocf_ni)
            if ocf_ni >= 1.0: components.append(3)
            elif ocf_ni >= 0.8: components.append(2)
            else: components.append(1)
        else:
            components.append(2)

        # FCF positivity
        if capex is not None and ocf is not None:
            fcf_observed_quarters += 1
            fcf = ocf - abs(capex)
            fcf_pos = 1 if fcf > 0 else 0
            if fcf_pos == 1:
                components.append(3)
                fcf_pos_quarters += 1
            else:
                components.append(1)
        else:
            components.append(2)

        q_score = sum(components) / len(components)
        quarterly_scores.append(q_score)

    # ---------- 3. Aggregate quality scores ----------
    if quarterly_scores:
        avg_score = np.mean(quarterly_scores)
        avg_gm = round(np.mean(gm_changes), 2) if gm_changes else None
        avg_sbc = round(np.mean(sbc_pcts), 2) if sbc_pcts else None
        avg_ocf = round(np.mean(ocf_nis), 2) if ocf_nis else None
        if avg_ocf is not None and np.isnan(avg_ocf):
            avg_ocf = None
        fcf_pos_count = fcf_pos_quarters if fcf_observed_quarters else None

        available = sum([avg_gm is not None, avg_sbc is not None,
                         avg_ocf is not None, fcf_pos_count is not None])
        if available < 2:
            quality = None
            hist_score = None
        else:
            if avg_score >= 2.5: quality = 'High'
            elif avg_score >= 1.5: quality = 'Medium'
            else: quality = 'Low'
            quality_map = {'High': 3, 'Medium': 2, 'Low': 1}
            hist_score = quality_map[quality]
    else:
        quality = None
        hist_score = None
        avg_gm = None; avg_sbc = None; avg_ocf = None; fcf_pos_count = None

 # ---------- 4. Capex sentiment (market data) ----------
    market_punishing = None
    conviction_penalty = None
    capex_trigger = None
    if sector == "Technology":
        # ---- XLK ETF return ----
        etf_return = None
        try:
            start_dl = as_of_date - timedelta(days=12)
            xlk = yf.download('XLK', start=start_dl, end=as_of_date - timedelta(days=1), progress=False)
            if len(xlk) >= 2:
                xlk = xlk.tail(5)
                etf_return = ((xlk['Close'].iloc[-1] / xlk['Close'].iloc[0] - 1) * 100).item()
                etf_return = float(etf_return)
        except:
            pass

        # ---- Downgrade count ----
        def rating_tier(grade):          # ← MOVED UP
            g = str(grade).lower()
            if g in ['buy','overweight','outperform']: return 2
            if g in ['hold','neutral','market perform','sector perform']: return 1
            if g in ['sell','underperform','underweight']: return 0
            return 1

        downgrade_count = 0
        try:
            # reuse the 'stock' object from line 16 (no need to create another one)
            downgrades = stock.upgrades_downgrades
            last14 = pd.Timestamp(as_of_date) - timedelta(days=14)
            mask = (downgrades.index >= last14) & (downgrades.index < pd.Timestamp(as_of_date))
            recent = downgrades[mask]
            for _, rrow in recent.iterrows():
                fr = rating_tier(rrow.get('FromGrade', ''))
                to = rating_tier(rrow.get('ToGrade', ''))
                if to < fr:
                    downgrade_count += 1
        except:
            downgrade_count = 0

        # ---- Determine market punishment and penalty ----
        if etf_return is not None and downgrade_count is not None:
            market_punishing = 1 if (etf_return < -3.0 and downgrade_count >= 2) else 0
        else:
            market_punishing = None

        if market_punishing == 1 and monetisation_latest == 0:
            if etf_return is not None and etf_return < -5.0 and rev_growth_latest is not None and rev_growth_latest < 0:
                conviction_penalty = 'Skip'
                capex_trigger = 1
            else:
                conviction_penalty = 'Reduce'
                capex_trigger = 1
        else:
            conviction_penalty = 'None'
            capex_trigger = 0
    else:
        # Non‑tech: SCS fields remain None
        pass

    return {
        'quality': hist_score,
        'avg_gm': avg_gm,
        'avg_sbc': avg_sbc,
        'avg_ocf': avg_ocf,
        'fcf_pos_count': fcf_pos_count,
        'yoy_growth_streak': yoy_growth_streak,
        'scs_market_punishing_capex': market_punishing,
        'scs_monetisation_evidence': monetisation_latest,
        'scs_conviction_penalty': conviction_penalty,
        'scs_capex_trigger_active': capex_trigger
    }

def current_earnings_quality(ticker, as_of_date):
    """Compute current‑quarter earnings quality, EPS beat, and GAAP profitability."""

    import numpy as np, pandas as pd, edgar, yfinance as yf
    from datetime import date, timedelta

    # ---------------- helper functions ----------------
    def last_day_of_month(year, month):
        days = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        if month == 2 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
            return 29
        return days[month]

    def quarter_end_from_fye(label, fye_str):
        try:
            q = int(label[1])               # e.g. 3 from 'Q3'
            fy = int(label.split()[1])      # e.g. 2026
            fye_month = int(fye_str[:2])    # e.g. 6
            fye_day   = int(fye_str[2:4])   # e.g. 30
        except:
            return None
        if q == 4:
            return date(fy, fye_month, fye_day)
        months_back = 3 * (4 - q)
        month = fye_month - months_back
        year = fy
        while month <= 0:
            month += 12
            year -= 1
        max_day = last_day_of_month(year, month)
        day = min(fye_day, max_day)
        return date(year, month, day)

    def get_value(df, label, quarter):
        try:
            row = df[df['label'] == label]
            if not row.empty:
                return row[quarter].iloc[0]
        except:
            pass
        return None

    # ---------------- 1. Try yfinance for EPS surprise ----------------
    eps_beat = None
    latest = None
    try:
        stock = yf.Ticker(ticker)
        ed = stock.earnings_dates
        if ed is not None and not ed.empty:
            reported = ed[ed['Reported EPS'].notna()]
            date_mask = reported.index.date < as_of_date
            reported = reported[date_mask]
            if not reported.empty:
                latest = reported.sort_index(ascending=False).iloc[0]
                surprise = latest.get('Surprise(%)')
                if surprise is not None and pd.notna(surprise):
                    eps_beat = 1 if surprise > 0 else 0
    except:
        pass

    # ---------------- 2. fetch EDGAR financials ----------------
    try:
        company = edgar.Company(ticker)
        facts = company.get_facts()
        income_df = facts.income_statement(periods=1000, annual=False, as_dataframe=True)
        cashflow_df = facts.cashflow_statement(periods=1000, annual=False, as_dataframe=True)
        fye_str = company.fiscal_year_end
    except:
        return None

    meta_cols = {'label', 'depth', 'is_abstract', 'is_total', 'section', 'confidence'}

    def safe_quarter(col):
        if col in meta_cols:
            return None
        q_end = quarter_end_from_fye(col, fye_str)
        if q_end is None or q_end > as_of_date:
            return None
        return q_end

    income_col_info = [(col, safe_quarter(col)) for col in income_df.columns]
    income_col_info = [x for x in income_col_info if x[1] is not None]
    income_col_info.sort(key=lambda x: x[1], reverse=True)
    valid_income_cols = [col for col, _ in income_col_info]

    cashflow_col_info = [(col, safe_quarter(col)) for col in cashflow_df.columns]
    cashflow_col_info = [x for x in cashflow_col_info if x[1] is not None]
    cashflow_col_info.sort(key=lambda x: x[1], reverse=True)
    valid_cf_cols = [col for col, _ in cashflow_col_info]

    if len(valid_income_cols) < 5:
        return None

    # ---------------- 3. extract line items (walk back up to 3 quarters) ----------------
    revenue_labels = [
        'Total Revenue',
        'Revenue, Net (Deprecated 2018-01-31)',
        'Sales Revenue, Goods, Net (Deprecated 2018-01-31)',
        'RevenueFromContractWithCustomerExcludingAssessedTax',
        'Revenues', 'Total net revenues', 'Total non-interest revenues',
        'Total interest income', 'Total revenues', 'Revenue from contracts with customers'
    ]
    cost_of_rev_labels = ['Cost of Revenue', 'CostOfGoodsAndServicesSold', 'CostOfRevenue']
    ni_labels = ['Net Income (Loss) Attributable to Parent', 'NetIncomeLoss']

    revenue_latest = None
    revenue_prev = None
    cost_of_rev_latest = None
    cost_of_rev_prev = None
    ni = None
    eps_latest = None
    eps_prev = None

    chosen_income_col = None
    for offset in range(min(3, len(valid_income_cols))):
        q_test = valid_income_cols[offset]
        for lbl in revenue_labels:
            val = get_value(income_df, lbl, q_test)
            if val is not None and pd.notna(val):
                chosen_income_col = q_test
                revenue_latest = val
                break
        if chosen_income_col is not None:
            break

    if chosen_income_col is not None:
        try:
            idx = valid_income_cols.index(chosen_income_col)
            if idx + 4 < len(valid_income_cols):
                prev_year_col = valid_income_cols[idx + 4]
                # Revenue prev
                for lbl in revenue_labels:
                    val = get_value(income_df, lbl, prev_year_col)
                    if val is not None and pd.notna(val):
                        revenue_prev = val
                        break
                # Cost of revenue
                for lbl in cost_of_rev_labels:
                    val = get_value(income_df, lbl, chosen_income_col)
                    if val is not None and pd.notna(val):
                        cost_of_rev_latest = val
                        break
                for lbl in cost_of_rev_labels:
                    val = get_value(income_df, lbl, prev_year_col)
                    if val is not None and pd.notna(val):
                        cost_of_rev_prev = val
                        break
                # Net income
                for lbl in ni_labels:
                    val = get_value(income_df, lbl, chosen_income_col)
                    if val is not None and pd.notna(val):
                        ni = val
                        break
                # EPS (for beat)
                eps_latest = get_value(income_df, 'EarningsPerShare, Diluted', chosen_income_col)
                if eps_latest is None or pd.isna(eps_latest):
                    eps_latest = get_value(income_df, 'EarningsPerShare, Basic', chosen_income_col)
                eps_prev = get_value(income_df, 'EarningsPerShare, Diluted', prev_year_col)
                if eps_prev is None or pd.isna(eps_prev):
                    eps_prev = get_value(income_df, 'EarningsPerShare, Basic', prev_year_col)
        except (IndexError, ValueError):
            pass

    # Do NOT treat year-over-year EPS growth as an analyst EPS beat.
    # Missing point-in-time consensus stays unknown (None).
    # EPS surprise percentage (continuous)
    eps_surprise_pct = None
    if latest is not None:
        surprise_val = latest.get('Surprise(%)')
        if surprise_val is not None and pd.notna(surprise_val):
            eps_surprise_pct = surprise_val
    # Do not substitute YoY EPS growth for EPS surprise.

    # Revenue surprise requires historical consensus estimates, not YoY growth.
    revenue_surprise_pct = None

    # ---------------- 4. cash flow items ----------------
    cf_latest_q = valid_cf_cols[0] if valid_cf_cols else None
    ocf = None
    sbc_q = None
    capex = None

    if cf_latest_q is not None:
        ocf_lbl = [
            "Net Cash Provided by (Used in) Operating Activities",
            "Net cash (used in) operating activities",
            "Operating Cash Flow",
            'NetCashProvidedByUsedInOperatingActivities'
        ]
        for k in ocf_lbl:
            val = get_value(cashflow_df, k, cf_latest_q)
            if val is not None and pd.notna(val):
                ocf = val
                break

        for lbl in ["ShareBasedCompensation",
                    "Share-based Payment Arrangement, Noncash Expense",
                    "Share-based Payment Arrangement, Expensed and Capitalized, Amount",
                    "Stock Based Compensation"]:
            try:
                val = cashflow_df.loc[lbl, cf_latest_q]
                if val is not None:
                    sbc_q = val.item() if hasattr(val, 'item') else val
                    break
            except (KeyError, IndexError):
                continue

        for lbl in ["Capital Expenditure", "Capital Expenditures",
                    "Payments to Acquire Property, Plant, and Equipment",
                    "PaymentsToAcquirePropertyPlantAndEquipment",
                    "CapitalExpendituresIncurredButNotYetPaid"]:
            try:
                raw = cashflow_df.loc[lbl, cf_latest_q]
                if raw is not None:
                    capex = raw.item() if hasattr(raw, 'item') else raw
                    break
            except (KeyError, IndexError):
                continue

    # ---------------- 5. yfinance fallback if income data is still missing ----------------
    if revenue_latest is None or ni is None:
        try:
            stock = yf.Ticker(ticker)
            q_income = stock.quarterly_financials
            q_cashflow = stock.quarterly_cashflow
            valid_inc = [c for c in q_income.columns if c.date() < as_of_date]
            valid_cf  = [c for c in q_cashflow.columns if c.date() < as_of_date]
            if valid_inc:
                latest_inc = sorted(valid_inc)[-1]
                if 'Total Revenue' in q_income.index:
                    revenue_latest = q_income.loc['Total Revenue', latest_inc]
                    if pd.isna(revenue_latest): revenue_latest = None
                if 'Cost Of Revenue' in q_income.index:
                    cost_of_rev_latest = q_income.loc['Cost Of Revenue', latest_inc]
                    if pd.isna(cost_of_rev_latest): cost_of_rev_latest = None
                if 'Net Income' in q_income.index:
                    ni = q_income.loc['Net Income', latest_inc]
                    if pd.isna(ni): ni = None
                prev_year_col = latest_inc - pd.DateOffset(years=1)
                if prev_year_col in q_income.columns:
                    if 'Total Revenue' in q_income.index:
                        revenue_prev = q_income.loc['Total Revenue', prev_year_col]
                        if pd.isna(revenue_prev): revenue_prev = None
                    if 'Cost Of Revenue' in q_income.index:
                        cost_of_rev_prev = q_income.loc['Cost Of Revenue', prev_year_col]
                        if pd.isna(cost_of_rev_prev): cost_of_rev_prev = None
            if ocf is None and valid_cf:
                latest_cf = sorted(valid_cf)[-1]
                if 'Operating Cash Flow' in q_cashflow.index:
                    ocf = q_cashflow.loc['Operating Cash Flow', latest_cf]
                    if pd.isna(ocf): ocf = None
                if 'Capital Expenditure' in q_cashflow.index:
                    capex = q_cashflow.loc['Capital Expenditure', latest_cf]
                    if pd.isna(capex): capex = None
                if 'Stock Based Compensation' in q_cashflow.index:
                    sbc_q = q_cashflow.loc['Stock Based Compensation', latest_cf]
                    if pd.isna(sbc_q): sbc_q = None
        except Exception:
            pass

    # ---------------- 6. compute derived metrics ----------------
    gm_change_bps = None
    if (all(v is not None and pd.notna(v) for v in
            [revenue_latest, cost_of_rev_latest, revenue_prev, cost_of_rev_prev])
            and revenue_latest > 0 and revenue_prev > 0):
        gm_latest = ((revenue_latest - cost_of_rev_latest) / revenue_latest) * 100
        gm_prev = ((revenue_prev - cost_of_rev_prev) / revenue_prev) * 100
        gm_change_bps = round((gm_latest - gm_prev) * 100, 2)

    sbc_pct = None
    if sbc_q is not None and revenue_latest is not None and revenue_latest > 0:
        sbc_pct = round((sbc_q / revenue_latest) * 100, 2)

    ocf_ni_ratio = None
    if ocf is not None and ni is not None and ni != 0:
        ocf_ni_ratio = round(ocf / ni, 2)

    fcf_positive = None
    if capex is not None and ocf is not None:
        # Treat capex as expenditure magnitude, regardless of source sign.
        fcf = ocf - abs(capex)
        fcf_positive = 1 if fcf > 0 else 0

    # GAAP profitability is based on GAAP net income, independent of SBC%.
    gaap_profit = int(ni > 0) if ni is not None and pd.notna(ni) else None

    # ---------------- 7. component scoring ----------------
    components = []

    if gm_change_bps is not None:
        if gm_change_bps >= 100: components.append(3)
        elif gm_change_bps >= 0: components.append(2)
        else: components.append(1)
    else:
        components.append(2)

    if sbc_pct is not None:
        if sbc_pct < 1.5: components.append(3)
        elif sbc_pct < 3: components.append(2)
        else: components.append(1)
    else:
        components.append(2)

    if ocf_ni_ratio is not None:
        if ocf_ni_ratio >= 1.0: components.append(3)
        elif ocf_ni_ratio >= 0.8: components.append(2)
        else: components.append(1)
    else:
        components.append(2)

    if fcf_positive is not None:
        if fcf_positive == 1: components.append(3)
        else: components.append(1)
    else:
        components.append(2)

    avg_score = sum(components) / len(components)
    if avg_score >= 2.5:
        quality = 'High'
    elif avg_score >= 1.5:
        quality = 'Medium'
    else:
        quality = 'Low'
    quality_map = {'High': 3, 'Medium': 2, 'Low': 1}
    score = quality_map[quality]

    # No historical analyst revenue estimate in this function.
    revenue_beat = None

    return {
        'quality': score,  # numeric: matches ml_dataset.quality_curr INTEGER
        'quality_label': quality,
        'score': score,
        'revenue_latest': revenue_latest,
        'revenue_prev': revenue_prev,
        'gm_change_bps': gm_change_bps,
        'sbc_pct': sbc_pct,
        'ocf_ni_ratio': ocf_ni_ratio,
        'fcf_positive': fcf_positive,
        'revenue_beat': revenue_beat,
        'eps_beat': eps_beat,
        'gaap_profit': gaap_profit,
        'eps_surprise_pct': eps_surprise_pct,
        'revenue_surprise_pct': revenue_surprise_pct
    }

def load_price_history(ticker):
    """Get daily OHLCV. Preserve 'close_price' for existing feature functions."""
    with sqlite3.connect(_feature_database_path()) as conn:
        df = pd.read_sql_query(
            """SELECT date, open, high, low, close,
                      close AS close_price, volume
                 FROM price_history
                WHERE ticker = ?
                ORDER BY date""",
            conn,
            params=(ticker,),
            parse_dates=['date'],
            index_col='date',
        )
    return df

def compute_runup(ticker, as_of_date, df_price):
    """Pre-event price change: prior close at T-14 calendar days to T-2."""
    if df_price is None or df_price.empty:
        return None
    cutoff = pd.Timestamp(as_of_date).normalize()
    start = df_price.loc[:cutoff - pd.Timedelta(days=14), 'close_price'].dropna()
    end = df_price.loc[:cutoff - pd.Timedelta(days=2), 'close_price'].dropna()
    if start.empty or end.empty:
        return None
    p0, p1 = float(start.iloc[-1]), float(end.iloc[-1])
    if not (np.isfinite(p0) and np.isfinite(p1)) or p0 <= 0 or p1 <= 0:
        return None
    if start.index[-1] >= end.index[-1]:
        return None
    return round((p1 / p0 - 1) * 100, 2)

def compute_rsi(ticker, as_of_date, df_price):
    """14-session RSI using simple moving averages (matches original convention)."""
    if df_price is None or df_price.empty:
        return None
    close = df_price.loc[:pd.Timestamp(as_of_date) - pd.Timedelta(days=1), 'close_price'].dropna()
    if len(close) < 15:
        return None
    delta = close.diff()
    gains = delta.clip(lower=0).rolling(14).mean()
    losses = -delta.clip(upper=0).rolling(14).mean()
    gain, loss = gains.iloc[-1], losses.iloc[-1]
    if pd.isna(gain) or pd.isna(loss):
        return None
    if gain == 0 and loss == 0:
        return 50.0
    if loss == 0:
        return 100.0
    if gain == 0:
        return 0.0
    return round(float(100 - 100 / (1 + gain / loss)), 2)

def compute_volume_ratio(ticker, as_of_date, df_price):
    if df_price.empty:
        return None

    # Use only data up to the day BEFORE the announcement (strictly pre‑announcement)
    pre_data = df_price.loc[:pd.Timestamp(as_of_date - timedelta(days=1))]

    if len(pre_data) < 21:   # need at least 21 rows to get 20 prior days + yesterday
        return None

    # Volume on the most recent day (which is the day before the announcement)
    yesterday_vol = pre_data['volume'].iloc[-1]

    # Average volume over the 20 days prior to that (i.e., the 20 days ending the day before)
    avg_20_vol = pre_data['volume'].iloc[-21:-1].mean()   # rows from -21 to -2 (20 rows)

    if avg_20_vol == 0 or pd.isna(yesterday_vol) or pd.isna(avg_20_vol):
        return None

    ratio = round(yesterday_vol / avg_20_vol, 2)
    return ratio

def load_earnings_dates(ticker):
    """Return chronologically sorted known earnings-event dates."""
    with sqlite3.connect(_feature_database_path()) as conn:
        df = pd.read_sql_query(
            """SELECT earnings_date FROM earnings_history
                WHERE ticker = ? ORDER BY earnings_date""",
            conn, params=(ticker,), parse_dates=['earnings_date'],
        )
    if df.empty:
        return pd.Series(dtype='datetime64[ns]')
    return df['earnings_date'].dropna().sort_values().reset_index(drop=True)

def compute_past_earnings_action(ticker, as_of_date, df_price, df_ed):
    """Past event reactions only when the full 20-session response is observable.

    Uses the close before the earnings date and sessions strictly AFTER it;
    report timings (pre-market vs after-hours) require a separate timestamp
    to make this a true execution-day response feature.
    """
    keys = ('surge_hold_count', 'fade_count', 'drop_count',
            'past_earnings_action', 'pct_surge', 'pullback_bounce_count',
            'avg_pullback_depth', 'past_pullback_bounce', 'post_earnings_drift')
    empty = dict.fromkeys(keys)
    if df_price is None or df_price.empty or df_ed is None or df_ed.empty:
        return empty
    cutoff = pd.Timestamp(as_of_date).normalize()
    prices = df_price.loc[:cutoff - pd.Timedelta(days=1), 'close_price'].dropna()
    if prices.empty:
        return empty
    dates = pd.to_datetime(df_ed, errors='coerce').dropna()
    past_dates = dates[dates < cutoff].sort_values(ascending=False)
    labels, reactions, depths, drifts = [], [], [], []
    for event in past_dates:
        if len(labels) >= 4:
            break
        event = pd.Timestamp(event).normalize()
        baseline = prices[prices.index < event]
        future = prices[prices.index > event]
        # Require the entire response window to be strictly before cutoff.
        if baseline.empty or len(future) < 20:
            continue
        p0 = float(baseline.iloc[-1])
        post = future.iloc[:20]
        p1, p5, p10 = map(float, (post.iloc[0], post.iloc[4], post.iloc[9]))
        if p0 <= 0 or not all(np.isfinite(x) and x > 0 for x in (p1, p5, p10)):
            continue
        if p1 > p0:
            gave_back = (p1 - p5) > 0.5 * (p1 - p0)
            labels.append('Fade' if gave_back else 'Surge & Hold')
        else:
            labels.append('Drop')
        peak = float(post.iloc[:5].max())
        peak_pos = int(np.argmax(post.iloc[:5].to_numpy()))
        following = post.iloc[peak_pos + 1:]
        if following.empty or peak <= 0:
            reactions.append('no bounce')
        else:
            lowest = float(following.min())
            pullback_pct = (lowest / peak - 1) * 100
            bounced = pullback_pct <= -2 and float(post.iloc[-1]) > peak
            reactions.append('pullback and bounce' if bounced else 'no bounce')
            if bounced:
                depths.append(pullback_pct)
        drifts.append((p10 / p0 - 1) * 100)
    if len(labels) < 2:
        return empty
    surge = labels.count('Surge & Hold')
    return {
        'surge_hold_count': surge,
        'fade_count': labels.count('Fade'),
        'drop_count': labels.count('Drop'),
        'past_earnings_action': max(set(labels), key=lambda x: (labels.count(x), x)),
        'pct_surge': round(surge / len(labels), 2),
        'pullback_bounce_count': reactions.count('pullback and bounce'),
        'avg_pullback_depth': round(float(np.mean(depths)), 2) if depths else None,
        'past_pullback_bounce': max(set(reactions), key=lambda x: (reactions.count(x), x)),
        'post_earnings_drift': round(float(np.mean(drifts)), 2) if drifts else None,
    }
    
def compute_prior_guidance_raised(ticker, as_of_date):

    # 1. Find the most recent earnings date before as_of_date
    ed_series = load_earnings_dates(ticker)   # your existing function
    past_dates = ed_series[ed_series < pd.Timestamp(as_of_date)]
    if past_dates.empty:
        return None
    prior_date = past_dates.sort_values(ascending=False).iloc[0].date()

    # 2. Fetch the 8‑K from that prior date
    try:
        company = edgar.Company(ticker)
        filings = company.get_filings(form="8-K",
                                      filing_date=f"{prior_date}:{prior_date}")
    except:
        return None
    # ---- helpers for keyword scan ----
    def has_item(filing, item_code):
        if filing.items is None:
            return False
        if isinstance(filing.items, str):
            return item_code in filing.items
        return any(item_code in str(it) for it in filing.items)

    # Single‑word indicators
    raise_words = [
        'raise', 'raises', 'raised', 'raising',
        'increase', 'increases', 'increased', 'increasing',
        'boost', 'boosts', 'boosted', 'boosting',
        'upgrade', 'upgrades', 'upgraded', 'upgrading'
    ]
    affirm_words = [
        'affirm', 'affirms', 'affirmed', 'affirming',
        'reaffirm', 'reaffirms', 'reaffirmed', 'reaffirming',
        'reiterate', 'reiterates', 'reiterated', 'reiterating',
        'maintain', 'maintains', 'maintained', 'maintaining',
        'unchanged', 'no change'
    ]

    for f in filings:
        # Only process 8‑Ks that contain Item 2.02
        if not has_item(f, '2.02'):
            continue
        try:
            text = f.obj().text()
        except:
            continue

        lower_text = text.lower()
        search_start = 0
        while True:
            idx = lower_text.find('guidance', search_start)
            if idx == -1:
                break
            start_idx = max(0, idx - 200)
            end_idx   = min(len(lower_text), idx + 500)
            snippet = lower_text[start_idx:end_idx]

            # Check for raise words with proximity & negation filter
            for word in raise_words:
                pos = snippet.find(word)
                if pos == -1:
                    continue
                snippet_guidance_pos = snippet.find('guidance')
                if abs(pos - snippet_guidance_pos) <= 100:
                    before_word = snippet[max(0, pos-20):pos]
                    if not any(neg in before_word for neg in ['not ', 'no ', 'may not ', 'without ']):
                        return 1   # raise detected

            for word in affirm_words:
                pos = snippet.find(word)
                if pos == -1:
                    continue
                snippet_guidance_pos = snippet.find('guidance')
                if abs(pos - snippet_guidance_pos) <= 100:
                    before_word = snippet[max(0, pos-20):pos]
                    if not any(neg in before_word for neg in ['not ', 'no ', 'may not ']):
                        return 0   # affirm detected

            search_start = idx + 1

    return None

def compute_sector_relative_strength(ticker, as_of_date, df_price):
    """Compute historical stock-vs-SPY momentum.

    Sector-dependent results intentionally unavailable without point-in-time
    sector membership. Legacy result keys are retained for the backfill.
    """
    empty = {'stock_vs_spy_20d': None,
             'stock_vs_sector_20d': None,
             'sector_spy_return_ratio': None}
    if df_price is None or df_price.empty:
        return empty
    close = df_price.loc[:pd.Timestamp(as_of_date) - pd.Timedelta(days=1), 'close_price'].dropna()
    if len(close) < 21:
        return empty
    end = pd.Timestamp(as_of_date).normalize()
    begin = end - pd.Timedelta(days=60)
    try:
        spy = yf.download('SPY', start=begin, end=end,
                          auto_adjust=False, progress=False)
        if spy is None or spy.empty:
            return empty
        spy_close = spy['Close']
        if isinstance(spy_close, pd.DataFrame):
            spy_close = spy_close.iloc[:, 0]
        spy_close = spy_close.dropna().astype(float)
        # Align on common actual sessions; prevents mismatched date endpoints.
        joined = pd.concat([close.rename('stock'), spy_close.rename('spy')], axis=1,
                           join='inner').dropna().tail(21)
        if len(joined) < 21:
            return empty
        stock_p0, stock_p1 = joined['stock'].iloc[0], joined['stock'].iloc[-1]
        spy_p0, spy_p1 = joined['spy'].iloc[0], joined['spy'].iloc[-1]
        if stock_p0 <= 0 or spy_p0 <= 0:
            return empty
        stock_ret = (stock_p1 / stock_p0 - 1) * 100
        spy_ret = (spy_p1 / spy_p0 - 1) * 100
        return {**empty, 'stock_vs_spy_20d': round(float(stock_ret - spy_ret), 2)}
    except Exception as exc:
        print(f'compute_sector_relative_strength({ticker}, {as_of_date}): {exc}')
        return empty
    
def compute_sue(ticker, as_of_date):
    """Return SUE (Standardized Unexpected Earnings) for the most recent quarter."""
    import yfinance as yf
    import pandas as pd
    import numpy as np

    try:
        stock = yf.Ticker(ticker)
        ed = stock.earnings_dates
        if ed is None or ed.empty:
            return None

        # Filter to quarters before as_of_date that have a reported EPS
        reported = ed[ed['Reported EPS'].notna()]
        date_mask = reported.index.date < as_of_date
        reported = reported[date_mask]
        if reported.empty:
            return None

        # Sorted most recent first
        reported = reported.sort_index(ascending=False)

        # Current quarter surprise
        current = reported.iloc[0]
        surprise = current.get('Surprise(%)')
        if surprise is None or pd.isna(surprise):
            return None

        # Last 8 quarters of surprises (excluding current)
        hist_surprises = reported.iloc[1:9]['Surprise(%)'].dropna()
        if len(hist_surprises) < 5:   # need at least 5 to compute a meaningful std
            return None

        std = hist_surprises.std()
        if std == 0:
            return None
        return round(surprise / std, 2)
    except:
        return None

def compute_historical_runup_avg(ticker, as_of_date, df_price, ed_series):

    if df_price.empty or ed_series.empty:
        return None

    # Past earnings dates strictly before as_of_date
    past_dates = ed_series[ed_series < pd.Timestamp(as_of_date)]
    if len(past_dates) < 2:
        return None

    recent_dates = past_dates.sort_values(ascending=False).head(4)
    runups = []
    for d in recent_dates:
        rup = compute_runup(ticker, d.date(), df_price)   # reuse the function you already have
        if rup is not None:
            runups.append(rup)
    if len(runups) < 2:
        return None
    return round(sum(runups) / len(runups), 2)

def compute_seasonality_match(ticker, as_of_date, df_price, ed_series):
    """
    Compare current quarter's run‑up sign with the average run‑up sign of the same
    fiscal quarter over the last 4 years. Returns 1 if signs match, 0 if they differ,
    None if insufficient data.
    """
    # Current quarter run‑up
    current_runup = compute_runup(ticker, as_of_date, df_price)
    if current_runup is None:
        return None

    # Filter past earnings to only those in the same fiscal quarter (same month range)
    # We'll use the month of as_of_date to define the quarter.
    target_month = as_of_date.month
    # All past earnings before as_of_date
    past_dates = ed_series[ed_series < pd.Timestamp(as_of_date)]
    if past_dates.empty:
        return None

    # Keep only those whose month is within ±1 month of the target month (same quarter)
    same_quarter_dates = past_dates[
        past_dates.dt.month.isin([(target_month - i) % 12 or 12 for i in range(-1, 2)])
    ]
    if len(same_quarter_dates) < 2:
        return None

    # Take the most recent 4 such quarters
    recent_same_quarter = same_quarter_dates.sort_values(ascending=False).head(4)
    hist_runups = []
    for d in recent_same_quarter:
        rup = compute_runup(ticker, d.date(), df_price)
        if rup is not None:
            hist_runups.append(rup)
    if len(hist_runups) < 2:
        return None

    avg_hist = sum(hist_runups) / len(hist_runups)
    current_sign = 1 if current_runup > 0 else 0
    hist_sign = 1 if avg_hist > 0 else 0
    return 1 if current_sign == hist_sign else 0

def compute_insider_transactions(ticker, as_of_date, max_filings=50):
    """Only Form 4s FILED before as_of_date; fetch a dated set first."""
    cutoff = pd.Timestamp(as_of_date).date()
    end = cutoff - timedelta(days=1)
    start = end - timedelta(days=90)
    try:
        filings = edgar.Company(ticker).get_filings(
            form='4', filing_date=f'{start.isoformat()}:{end.isoformat()}'
        ).head(max_filings)
    except Exception as exc:
        print(f'compute_insider_transactions({ticker}, {as_of_date}): {exc}')
        return None
    buys = sells = 0
    buy_value = sell_value = 0.0
    saw_usable = False
    for filing in filings:
        filed = pd.Timestamp(filing.filing_date).date()
        if not start <= filed < cutoff:
            continue
        try:
            summary = filing.obj().get_ownership_summary()
            if summary is None:
                continue
            activity = str(summary.primary_activity).lower()
            amount = summary.net_value
            if amount is None or not np.isfinite(float(amount)):
                continue
            saw_usable = True
            if activity == 'purchase':
                buys += 1
                buy_value += abs(float(amount))
            elif activity == 'sale':
                sells += 1
                sell_value += abs(float(amount))
        except Exception:
            continue
    if not saw_usable:
        return None
    net = buy_value - sell_value
    return {'insider_flag': int(net > 0), 'net_value': round(net, 2),
            'buy_count': buys, 'sell_count': sells}

def compute_eps_rev_streak(ticker, as_of_date, ed_series):
    """EPS actual-vs-consensus beat streak known prior to the cutoff.

    Historical revenue consensus is unavailable: revenue_streak stays None.
    Zero means a known miss; None means the data is unavailable.
    """
    result = {'revenue_streak': None, 'eps_streak': None}
    try:
        dates = yf.Ticker(ticker).earnings_dates
        if dates is None or dates.empty or 'Surprise(%)' not in dates.columns:
            return result
        dates = dates.copy()
        dates.index = pd.to_datetime(dates.index, utc=True)
        cutoff = pd.Timestamp(as_of_date)
        cutoff = cutoff.tz_localize('UTC') if cutoff.tzinfo is None else cutoff.tz_convert('UTC')
        earlier = dates[dates.index < cutoff].sort_index(ascending=False)
        if earlier.empty:
            return result
        streak = 0
        for surprise in earlier['Surprise(%)'].head(4):
            if pd.isna(surprise):
                break
            if float(surprise) > 0:
                streak += 1
            else:
                break
        return {'revenue_streak': None, 'eps_streak': streak}
    except Exception as exc:
        print(f'compute_eps_rev_streak({ticker}, {as_of_date}): {exc}')
        return result

def get_market_context(as_of_date):
    """VIX close and 1-day oil move from sessions strictly preceding date."""
    cutoff = pd.Timestamp(as_of_date).normalize()
    start = cutoff - pd.Timedelta(days=15)
    result = {'vix_level': None, 'oil_move_1d': None}
    for ticker, key in (('^VIX', 'vix_level'), ('CL=F', 'oil_move_1d')):
        try:
            data = yf.download(ticker, start=start, end=cutoff,
                               auto_adjust=False, progress=False)
            if data is None or data.empty:
                continue
            closes = data['Close']
            if isinstance(closes, pd.DataFrame):
                closes = closes.iloc[:, 0]
            closes = closes.dropna().astype(float)
            if key == 'vix_level' and len(closes) >= 1:
                result[key] = round(float(closes.iloc[-1]), 2)
            if key == 'oil_move_1d' and len(closes) >= 2:
                old, new = float(closes.iloc[-2]), float(closes.iloc[-1])
                if old > 0 and new > 0:
                    result[key] = round((new / old - 1) * 100, 2)
        except Exception as exc:
            print(f'get_market_context({ticker}, {as_of_date}): {exc}')
    return result
    
def compute_pct_from_52wlow(ticker, as_of_date, df_price):
    """Percentage above lowest observed low over approximately 52 weeks."""
    if df_price is None or df_price.empty:
        return None
    cutoff = pd.Timestamp(as_of_date) - pd.Timedelta(days=1)
    window = df_price.loc[:cutoff].tail(252)
    if len(window) < 100:
        return None
    low_column = 'low' if 'low' in window.columns else 'close_price'
    low = window[low_column].min()
    latest_close = window['close_price'].iloc[-1]
    if pd.isna(low) or pd.isna(latest_close) or low <= 0:
        return None
    return round((float(latest_close) / float(low) - 1) * 100, 2)

def compute_market_cap_features(ticker, as_of_date, df_price):
    """Do not mix today's share count with a historical price.

    Add a point-in-time shares-outstanding table before enabling these fields.
    """
    return {'market_cap_bucket': None, 'log_market_cap': None}
    
def compute_sector_industry(ticker, as_of_date=None):
    """For historical backfills, requires point-in-time classification history.

    Pass as_of_date=historical_event_date from the backfill script. No current
    classification is used for historical events.
    """
    if as_of_date is not None:
        return {'sector': None, 'industry': None}
    try:
        info = yf.Ticker(ticker).info
        return {'sector': info.get('sector'), 'industry': info.get('industry')}
    except Exception as exc:
        print(f'compute_sector_industry({ticker}): {exc}')
        return {'sector': None, 'industry': None}
    
def compute_momentum_features(as_of_date, df_price):
    try:
        if df_price.empty:
            return None
        pre_data = df_price.loc[:pd.Timestamp(as_of_date - timedelta(days=1))]
        close_now = pre_data.iloc[-1]["close_price"]
        if pd.isna(close_now):
            return None
        out = {}
        if len(pre_data) >= 21:
            out["return_20d"] = round((close_now / pre_data.iloc[-21]["close_price"] - 1) * 100, 2)
        else:
            out["return_20d"] = None
        if len(pre_data) >= 61:
            out["return_60d"] = round((close_now / pre_data.iloc[-61]["close_price"] - 1) * 100, 2)
        else:
            out["return_60d"] = None
        if len(pre_data) >= 121:
            out["return_120d"] = round((close_now / pre_data.iloc[-121]["close_price"] - 1) * 100, 2)
        else:
            out["return_120d"] = None
        return out
    except Exception:
        return {
        'return_20d': None,
        'return_60d': None,
        'return_120d': None
    }

def compute_volatility_features(as_of_date, df_price):
    try:
        if df_price.empty:
            return None
        pre_data = df_price.loc[:pd.Timestamp(as_of_date - timedelta(days=1))]
        if pre_data.empty or len(pre_data) < 21:
            return None
        returns = pre_data["close_price"].pct_change().dropna()
        if returns.empty:
            return None
        vol20 = None
        vol60 = None
        if len(returns) >= 20:
            vol20 = returns.tail(20).std() * np.sqrt(252) * 100
        if len(returns) >= 60:
            vol60 = returns.tail(60).std() * np.sqrt(252) * 100
        return {
            "volatility_20d": round(float(vol20), 2) if vol20 is not None and not pd.isna(vol20) else None,
            "volatility_60d": round(float(vol60), 2) if vol60 is not None and not pd.isna(vol60) else None,
        }
    except Exception:
        return {
            "volatility_20d": None,
            "volatility_60d": None
        }

def compute_volatility_percentile(ticker, as_of_date, df_price, hist_years=2):
    """Rank current 20-return annualized HV against past 20-return HV values."""
    if df_price is None or df_price.empty:
        return None
    cutoff = pd.Timestamp(as_of_date).normalize()
    closes = df_price.loc[:cutoff - pd.Timedelta(days=1), 'close_price'].dropna()
    if len(closes) < 126:
        return None
    daily_returns = closes.pct_change()
    hv20_series = daily_returns.rolling(20).std() * np.sqrt(252) * 100
    current = hv20_series.iloc[-1]
    if pd.isna(current) or not np.isfinite(current):
        return None
    start = cutoff - pd.Timedelta(days=365 * hist_years)
    # The current observation must not rank against itself.
    historical = hv20_series[(hv20_series.index >= start) &
                             (hv20_series.index < hv20_series.index[-1])].dropna()
    if len(historical) < 20:
        return None
    percentile = float((historical < current).mean() * 100)
    return {'hv20_current': round(float(current), 2),
            'vol_percentile': round(percentile, 2),
            'high_vol_regime': int(percentile >= 80)}

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import pandas as pd

# FinBERT loads lazily only if compute_guidance_bert is called.

def compute_guidance_bert(ticker, as_of_date):
    """Score historical Item 2.02 guidance snippets with the stored classifier.

    Keeps original maximum-snippet aggregation for backward compatibility;
    note that this may be overconfident as snippet count grows.
    """
    ed_series = load_earnings_dates(ticker)
    cutoff = pd.Timestamp(as_of_date).normalize()
    older = ed_series[ed_series < cutoff]
    if older.empty:
        return -1
    day = pd.Timestamp(older.max()).date()
    try:
        filings = edgar.Company(ticker).get_filings(form='8-K',
                    filing_date=f'{day.isoformat()}:{day.isoformat()}')
    except Exception as exc:
        print(f'compute_guidance_bert({ticker}): {exc}')
        return -1
    keywords = ('guidance', 'outlook', 'forecast', 'expects', 'expect',
                'projects', 'projected', 'raises', 'raising', 'reaffirms',
                'affirms', 'maintains', 'updates', 'financial outlook',
                'sees', 'anticipates')
    snippets = set()
    for filing in filings:
        try:
            items = str(filing.items)
            if '2.02' not in items or pd.Timestamp(filing.filing_date).date() >= cutoff.date():
                continue
            text = filing.obj().text().lower()
            for keyword in keywords:
                pos = 0
                while True:
                    i = text.find(keyword, pos)
                    if i == -1:
                        break
                    snippets.add(text[max(0, i-300):min(len(text), i+500)])
                    pos = i + len(keyword)
        except Exception:
            continue
    if not snippets:
        return -1
    tokenizer, model = _get_guidance_model()
    scores = []
    for snippet in snippets:
        tokens = tokenizer(snippet, truncation=True, return_tensors='pt')
        with torch.no_grad():
            logits = model(**tokens).logits
            scores.append(float(torch.softmax(logits, dim=-1)[0, 1]))
    return max(scores)
