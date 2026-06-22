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

def analyst_momentum(ticker, as_of_date):
    import yfinance as yf
    import pandas as pd
    from datetime import timedelta

    def rating_tier(grade):
        grade_lower = str(grade).lower()
        if grade_lower in ['buy','overweight','outperform']:
            return 2
        elif grade_lower in ['hold','neutral','market perform','sector perform']:
            return 1
        elif grade_lower in ['sell','underperform','underweight']:
            return 0
        return 1

    try:
        stock = yf.Ticker(ticker)
        downgrades = stock.upgrades_downgrades
        
        # 1. Check if the historical dataframe itself exists and contains data
        has_history = downgrades is not None and not downgrades.empty
        
        # 2. Check if a general consensus mean exists in stock.info
        # (Some stocks have historical logs but no active mean, or vice versa)
        info_dict = stock.info if hasattr(stock, 'info') else {}
        rec_mean = info_dict.get("recommendationMean")
        has_mean = rec_mean is not None
        
        # 3. Calculate the coverage flag (1 if either indicator proves Wall Street looks at it, else 0)
        has_analyst_coverage = 1 if (has_history or has_mean) else 0

        # Scenario A: The API works, but there is absolutely no analyst history
        if not has_history:
            return {
                "recommendation_mean": rec_mean,
                "upgrade_count": 0,
                "downgrade_count": 0,
                "net_analyst_momentum": 0,
                "has_analyst_coverage": has_analyst_coverage,  # Will be 0 (or 1 if only mean exists)
            }

        # The index can be a DatetimeIndex or a plain integer index.
        # If it's a DatetimeIndex, use it directly; otherwise, look for a 'date' column.
        if pd.api.types.is_datetime64_any_dtype(downgrades.index):
            date_series = downgrades.index
        else:
            # Try common date columns
            for col in ['date', 'Date', 'filing_date', 'Filing Date']:
                if col in downgrades.columns:
                    date_series = pd.to_datetime(downgrades[col])
                    break
            else:
                # No date column – return neutral
                return {
                    'recommendation_mean': rec_mean,
                    'upgrade_count': 0,
                    'downgrade_count': 0,
                    'net_analyst_momentum': 0,
                    "has_analyst_coverage": has_analyst_coverage
                }

        last2weeks = pd.Timestamp(as_of_date) - timedelta(days=14)
        mask = (date_series >= last2weeks) & (date_series < pd.Timestamp(as_of_date))
        recent = downgrades[mask]

        upgrade_count = 0
        downgrade_count = 0
        for _, rrow in recent.iterrows():
            grade_from = rating_tier(rrow.get('FromGrade', ''))
            grade_to = rating_tier(rrow.get('ToGrade', ''))
            if grade_to < grade_from:
                downgrade_count += 1
            if grade_to > grade_from:
                upgrade_count += 1

        net = upgrade_count - downgrade_count
        return {
            'recommendation_mean': rec_mean,
            'upgrade_count': upgrade_count,
            'downgrade_count': downgrade_count,
            'net_analyst_momentum': net,
            "has_analyst_coverage": has_analyst_coverage
        }
    
    except Exception:
        return {
            'recommendation_mean': None,
            'upgrade_count': None,
            'downgrade_count': None,
            'net_analyst_momentum': None,
            "has_analyst_coverage": None
        }

def analyst_consensus(ticker, as_of_date):
    import yfinance as yf

    mom = analyst_momentum(ticker, as_of_date)
    consensus_proxy = 1 if (mom and mom['net_analyst_momentum'] and mom['net_analyst_momentum'] > 0) else 0
    return consensus_proxy


def analyst_revision(ticker, as_of_date):
    def rating_tier(grade):
        grade_lower = str(grade).lower()
        if grade_lower in ['buy','overweight','outperform']:
            return 2   # bullish
        elif grade_lower in ['hold','neutral','market perform','sector perform']:
            return 1   # neutral
        elif grade_lower in ['sell','underperform','underweight']:
            return 0   # bearish
        return 1  # unknown -> treat as neutral
    try:
        stock = yf.Ticker(ticker)
        downgrades = stock.upgrades_downgrades
        if downgrades is None or downgrades.empty:
            return {
                "upward_revision_count60d": None,
                "downward_revision_count60d": None,
                "net_revision_count_60d": None,
                "revision_breadth_60d": 0.5,
                "revision_trend_label": None,
                "estimate_revision_pct": None,
            }
        if not pd.api.types.is_datetime64_any_dtype(downgrades.index):
            return {
                "upward_revision_count60d": None,
                "downward_revision_count60d": None,
                "net_revision_count_60d": None,
                "revision_breadth_60d": 0.5,
                "revision_trend_label": None,
                "estimate_revision_pct": None,
            }
        last60days = pd.Timestamp(as_of_date) - timedelta(days=60)
        mask = (downgrades.index >= last60days) & (downgrades.index < pd.Timestamp(as_of_date))
        recent = downgrades[mask]
        downgrade_count = 0
        upgrade_count = 0
        breadth = None
        net_revision_count_60d = None
        label = None
        for _, rrow in recent.iterrows():
            grade_from = rating_tier(rrow.get('FromGrade', ''))
            grade_to = rating_tier(rrow.get('ToGrade', ''))
            if grade_to < grade_from:
                downgrade_count += 1
            if grade_to > grade_from:
                upgrade_count += 1
        if downgrade_count and upgrade_count:
            net_revision_count_60d = upgrade_count - downgrade_count
            breadth = upgrade_count / (upgrade_count + downgrade_count)
        else:
            upgrade_count = None
            downgrade_count = None
            breadth = 0.5
        if net_revision_count_60d is not None:
            if net_revision_count_60d > 3 and breadth > 0.7:
                label = "Strong Positive"
            elif net_revision_count_60d > 0:
                label = "Positive"
            elif net_revision_count_60d == 0:
                label = "Neutral"
            elif net_revision_count_60d < 0 and breadth < 0.3:
                label = "Strong Negative"
            else:
                label = "Negative"
        else:
            label = "No Revision Data"

        earnings = stock.earnings_dates
        revision_pct = None
        if earnings is not None and not earnings.empty:
            # Sort descending so most recent quarters are first
            earnings_sorted = earnings.sort_index(ascending=False)
            # Upcoming quarter: no reported EPS yet
            upcoming = earnings_sorted[earnings_sorted['Reported EPS'].isna()].head(1)
            if not upcoming.empty:
                current_est = upcoming['EPS Estimate'].iloc[0]
                # Most recently completed quarter: has a reported EPS
                completed = earnings_sorted[earnings_sorted['Reported EPS'].notna()].head(1)
                if not completed.empty:
                    prev_est = completed['EPS Estimate'].iloc[0]   # final estimate for that quarter
                    if pd.notna(current_est) and pd.notna(prev_est) and prev_est != 0:
                        revision_pct = round((current_est - prev_est) / abs(prev_est) * 100, 2)
        dictionary = {
            'upward_revision_count60d': upgrade_count,
            'downward_revision_count60d': downgrade_count,
            'net_revision_count_60d': net_revision_count_60d,
            'revision_breadth_60d': breadth,
            'revision_trend_label': label,
            'estimate_revision_pct': revision_pct
        }
        return dictionary
    except Exception:
        return {
                "upward_revision_count60d": None,
                "downward_revision_count60d": None,
                "net_revision_count_60d": None,
                "revision_breadth_60d": 0.5,
                "revision_trend_label": None,
                "estimate_revision_pct": None,
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
                if (capex / revenue_latest) < 0.05:
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
        if all(v is not None for v in [revenue_latest, cost_of_rev_latest, revenue_prev, cost_of_rev_prev]):
            gm_latest = ((revenue_latest - cost_of_rev_latest) / revenue_latest) * 100
            gm_prev = ((revenue_prev - cost_of_rev_prev) / revenue_prev) * 100
            gm_change = round(gm_latest - gm_prev, 2)
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
        if capex is not None:
            fcf = ocf + capex if ocf is not None else None
            fcf_pos = 1 if (fcf is not None and fcf > 0) else 0
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
        fcf_pos_count = fcf_pos_quarters if fcf_pos_quarters > 0 else None

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
    try:
        stock = yf.Ticker(ticker)
        ed = stock.earnings_dates
        if ed is not None and not ed.empty:
            reported = ed[(ed['Reported EPS'].notna()) & (ed.index < pd.Timestamp(as_of_date))]
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
                eps_latest = get_value(income_df, 'EarningsPerShareDiluted', chosen_income_col)
                if eps_latest is None or pd.isna(eps_latest):
                    eps_latest = get_value(income_df, 'EarningsPerShareBasic', chosen_income_col)
                eps_prev = get_value(income_df, 'EarningsPerShareDiluted', prev_year_col)
                if eps_prev is None or pd.isna(eps_prev):
                    eps_prev = get_value(income_df, 'EarningsPerShareBasic', prev_year_col)
        except (IndexError, ValueError):
            pass

    # If yfinance didn't give a beat, try EDGAR YoY growth
    if eps_beat is None:
        if eps_latest is not None and eps_prev is not None and eps_prev != 0:
            eps_beat = 1 if eps_latest > eps_prev else 0
    # EPS surprise percentage (continuous)
    eps_surprise_pct = None
    if 'latest' in dir() and latest is not None:
        surprise_val = latest.get('Surprise(%)')
        if surprise_val is not None and pd.notna(surprise_val):
            eps_surprise_pct = surprise_val
    # Fallback: YoY EPS growth from EDGAR
    if eps_surprise_pct is None and eps_latest is not None and eps_prev is not None and eps_prev != 0:
        eps_surprise_pct = round(((eps_latest - eps_prev) / abs(eps_prev)) * 100, 2)

    # Revenue surprise (continuous YoY growth proxy)
    revenue_surprise_pct = None
    if revenue_latest is not None and revenue_prev is not None and revenue_prev > 0:
        revenue_surprise_pct = round(((revenue_latest - revenue_prev) / revenue_prev) * 100, 2)

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
    if all(v is not None for v in [revenue_latest, cost_of_rev_latest, revenue_prev, cost_of_rev_prev]):
        gm_latest = ((revenue_latest - cost_of_rev_latest) / revenue_latest) * 100
        gm_prev = ((revenue_prev - cost_of_rev_prev) / revenue_prev) * 100
        gm_change_bps = round(gm_latest - gm_prev, 2)

    sbc_pct = None
    if sbc_q is not None and revenue_latest is not None and revenue_latest > 0:
        sbc_pct = round((sbc_q / revenue_latest) * 100, 2)

    ocf_ni_ratio = None
    if ocf is not None and ni is not None and ni != 0:
        ocf_ni_ratio = round(ocf / ni, 2)

    fcf_positive = None
    if capex is not None and ocf is not None:
        fcf = ocf + capex
        fcf_positive = 1 if fcf > 0 else 0

    # GAAP profitability (requires ni, sbc_pct)
    gaap_profit = None
    if ni is not None and sbc_pct is not None:
        gaap_profit = 1 if (ni > 0 and sbc_pct < 3.0) else 0

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

    revenue_beat = 1 if (revenue_latest is not None and revenue_prev is not None and
                         revenue_prev > 0 and revenue_latest > revenue_prev) else 0
    
    return {
        'quality': quality,
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
    """Return a DataFrame of all price history for a ticker, or an empty DataFrame."""
    import sqlite3, pandas as pd
    conn = sqlite3.connect('data/universe.db')
    df = pd.read_sql(f"""
        SELECT date, close_price, volume FROM price_history
        WHERE ticker = '{ticker}'
        ORDER BY date
    """, conn, parse_dates=['date'], index_col='date')
    conn.close()
    return df

def compute_runup(ticker, as_of_date, df_price):
    """Return pre‑earnings run‑up (%). df_price must contain all history for the ticker."""
    if df_price.empty or len(df_price) < 15:
        return None
    d14 = as_of_date - timedelta(days=14)
    d2  = as_of_date - timedelta(days=2)
    try:
        close_before = df_price.loc[:d2].iloc[-1]['close_price']
        close_start  = df_price.loc[:d14].iloc[-1]['close_price']
        if close_start == 0: return None
        return round(((close_before - close_start) / close_start) * 100, 2)
    except:
        return None

def compute_rsi(ticker, as_of_date, df_price):
    if df_price.empty or len(df_price) < 15:
        return None
    delta = df_price['close_price'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    RS = avg_gain / avg_loss
    RSI = 100 - (100 / (1 + RS))
    # Get the last RSI value on or before as_of_date
    rsi_series = RSI.loc[:pd.Timestamp(as_of_date - timedelta(days=1))]
    if rsi_series.empty:
        return None
    latest_rsi = round(rsi_series.iloc[-1], 2)
    if pd.isna(latest_rsi):
        return None
    return round(latest_rsi, 2)

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
    import sqlite3, pandas as pd
    conn = sqlite3.connect('data/universe.db')
    df = pd.read_sql(f"""
        SELECT earnings_date FROM earnings_history
        WHERE ticker = '{ticker}'
        ORDER BY earnings_date
    """, conn, parse_dates=['earnings_date'])
    conn.close()
    if df.empty:
        return pd.Series(dtype='datetime64[ns]')
    return df['earnings_date']

def compute_past_earnings_action(ticker, as_of_date, df_price, df_ed):
    def get_close_prev(df, target):
        try:
            return df.loc[target, 'close_price']
        except KeyError:
            idx = df.index.get_indexer([target], method='ffill')[0]
            return df.iloc[idx]['close_price']

    if df_price.empty or df_ed.empty:
        return None

    # Past earnings dates ≤ as_of_date
    earnings_hist = df_ed
    past = earnings_hist[earnings_hist < pd.Timestamp(as_of_date)]
    if len(past) < 2:
        return None

    recent = past.sort_index().tail(4)   # Series of datetime dates

    historical_action = []   # Surge & Hold / Fade / Drop
    reactions = []           # "pullback and bounce" / "no bounce"
    drift_values = []
    pullback_bounce_sum = 0.0

    for ed_date in recent:
        d0 = ed_date.date()
        d1 = d0 + timedelta(days=1)
        d5 = d0 + timedelta(days=5)

        # ------- Past earnings action (Surge & Hold / Fade / Drop) -------
        try:
            close0 = get_close_prev(df_price, d0)
            idx1 = df_price.index.get_indexer([d1], method='bfill')[0]
            idx5 = df_price.index.get_indexer([d5], method='ffill')[0]

            if idx1 < 0 or idx1 >= len(df_price) or idx5 >= len(df_price):
                continue
            close1 = df_price['close_price'].iloc[idx1]
            close5 = df_price['close_price'].iloc[idx5]
            if pd.isna(close0) or pd.isna(close1) or pd.isna(close5) or close0 == 0:
                continue
            return01 = (close1 - close0) / close0 * 100

            if return01 > 0:
                initial_gain = close1 - close0
                loss_from_peak = max(0, close1 - close5)
                gave_back = loss_from_peak > 0.5 * initial_gain
                label = 'Fade' if gave_back else 'Surge & Hold'
            else:
                label = 'Drop'
            historical_action.append(label)
        except:
            pass

        # ------- Pullback & Bounce -------
        try:
            idx1_pb = df_price.index.get_indexer([d1], method='bfill')[0]
            window20 = df_price.iloc[idx1_pb : idx1_pb + 20]
            if len(window20) < 20:
                continue
            first5 = window20.iloc[:5]
            post_high = first5['close_price'].max()
            high_date = first5[first5['close_price'] == post_high].index[0]
            high_pos = window20.index.get_loc(high_date)

            remaining = window20.iloc[high_pos + 1:]
            if remaining.empty:
                continue
            pull_back = remaining['close_price'].min()
            final_close = window20['close_price'].iloc[-1]
            pullback_pct = (pull_back - post_high) / post_high
            if pullback_pct <= -0.02 and final_close > post_high:
                reactions.append('pullback and bounce')
                pullback_bounce_sum += pullback_pct
            else:
                reactions.append('no bounce')
        except:
            pass

        try:
            earnings_date = ed_date
            idx = df_price.index.get_indexer([earnings_date], method="ffill")[0]
            if idx < 0 or idx + 10 >= len(df_price):
                print(f"{ticker} - not enough data")
                continue
            close_start = df_price['close_price'].iloc[idx]
            idx10 = idx + 10
            close_end = df_price['close_price'].iloc[idx10]

            if pd.isna(close_start) or pd.isna(close_end) or close_start == 0:
                print(f"{ticker}: invalid price data for {earnings_date}, skipping event")
                continue

            value = ((close_end - close_start)/close_start)*100
            drift_values.append(value)
        except:
            pass

    # ----- After processing all 4 events, summarise -----
    if len(historical_action) < 2:
        surge_count = fade_count = drop_count = pct_surge = most_common_action = None
    else:
        surge_count = historical_action.count('Surge & Hold')
        fade_count = historical_action.count('Fade')
        drop_count = historical_action.count('Drop')
        total_hist = len(historical_action)
        pct_surge = round(surge_count / total_hist, 2) if total_hist else None
        most_common_action = max(historical_action, key=historical_action.count)

    if len(reactions) < 2:
        pb_count = avg_depth = most_common_reaction = None
    else:
        pb_count = reactions.count('pullback and bounce')
        avg_depth = round((pullback_bounce_sum * 100) / pb_count, 2) if pb_count > 0 else None
        most_common_reaction = max(reactions, key=reactions.count)

    if len(drift_values) < 2:
            print(f"{ticker}: not enough data")
            avg_drift = None
    else:
        avg_drift = round(float(np.mean(drift_values)), 2)
    return {
        'surge_hold_count': surge_count,
        'fade_count': fade_count,
        'drop_count': drop_count,
        'past_earnings_action': most_common_action,
        'pct_surge': pct_surge,
        'pullback_bounce_count': pb_count,
        'avg_pullback_depth': avg_depth,
        'past_pullback_bounce': most_common_reaction,
        'post_earnings_drift': avg_drift
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
    """Return sector‑relative strength (sector ETF - SPY return) over 20 trading days."""
    import yfinance as yf
    import pandas as pd
    import numpy as np

    sector_to_etf = {
        "Financial Services": "XLF",
        "Technology": "XLK",
        "Consumer Defensive": "XLP",
        "Consumer Cyclical": "XLY",
        "Healthcare": "XLV",
        "Energy": "XLE",
        "Industrials": "XLI",
        "Basic Materials": "XLB",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
        "Communication Services": "XLC",
        "Consumer Staples": "XLP"
    }
    stock = yf.Ticker(ticker)
    if df_price.empty:
        return None
    pre_data = df_price.loc[:pd.Timestamp(as_of_date - timedelta(days=1))]

    sector = stock.info.get('sector', None)
    etf = sector_to_etf.get(sector)
    if etf is None:
        return None

    try:
        start = as_of_date - pd.offsets.BDay(20)
        xlk = yf.download(etf, start=start, end=(as_of_date - timedelta(days=1)), progress=False)
        spy = yf.download('SPY', start=start, end=(as_of_date - timedelta(days=1)), progress=False)

        if xlk.empty or spy.empty:
            return None

        # Use last valid close (drop NaN)
        xlk_close = xlk['Close'].dropna()
        spy_close = spy['Close'].dropna()
        if len(xlk_close) < 2 or len(spy_close) < 2:
            return None

        # Get start and end prices (earliest and latest valid)
        xlk_start = xlk_close.iloc[0]
        xlk_end = xlk_close.iloc[-1]
        spy_start = spy_close.iloc[0]
        spy_end = spy_close.iloc[-1]

        sector_ret = (xlk_end / xlk_start - 1) * 100
        spy_ret   = (spy_end / spy_start - 1) * 100

        # Stock return: use pre_data and drop NaN
        pre = pre_data[pre_data.index >= start]
        pre_close = pre['close_price'].dropna()
        if len(pre_close) < 2:
            stock_ret = None
        else:
            stock_start = pre_close.iloc[0]
            stock_end   = pre_close.iloc[-1]
            stock_ret   = (stock_end / stock_start - 1) * 100

        return {
            "stock_vs_spy_20d": round(float(stock_ret - spy_ret), 2) if stock_ret is not None else None,
            "stock_vs_sector_20d": round(float(stock_ret - sector_ret), 2) if stock_ret is not None else None,
            "sector_spy_return_ratio": round(sector_ret - spy_ret, 2)
        }
    except:
        return None
    
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
        reported = ed[(ed['Reported EPS'].notna()) & (ed.index < pd.Timestamp(as_of_date))]
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
    import edgar
    import datetime

    try:
        company = edgar.Company(ticker)
        form4s = company.get_filings(form="4").head(max_filings)
    except:
        return None

    total_buy_value = 0.0
    total_sell_value = 0.0
    buy_count = 0
    sell_count = 0
    filing_count = 0

    for f in form4s:
        # Robust handling: filing_date may be date or datetime
        filing_dt = f.filing_date
        if isinstance(filing_dt, datetime.datetime):
            filing_date = filing_dt.date()
        else:
            filing_date = filing_dt   # already a datetime.date

        if filing_date >= as_of_date:
            continue   # skip future filings

        try:
            ownership = f.obj()
            summary = ownership.get_ownership_summary()
            if summary is None:
                continue
            if summary.primary_activity == 'Purchase':
                total_buy_value += summary.net_value
                buy_count += 1
            elif summary.primary_activity == 'Sale':
                total_sell_value += abs(summary.net_value)
                sell_count += 1
            filing_count += 1
        except:
            continue

    if filing_count == 0:
        return None

    net_value = total_buy_value - total_sell_value
    insider_flag = 1 if net_value > 0 else 0
    return {
        'insider_flag': insider_flag,
        'net_value': round(net_value, 2),
        'buy_count': buy_count,
        'sell_count': sell_count
    }

def compute_eps_rev_streak(ticker, as_of_date, ed_series):
    past = ed_series[ed_series < pd.Timestamp(as_of_date)]
    if past.empty:
        return {'revenue_streak': 0, 'eps_streak': 0}

    recent = past.sort_values(ascending=False).head(4)
    rev_streak = 0
    eps_streak = 0
    rev_alive = True
    eps_alive = True

    for d in recent:
        res = current_earnings_quality(ticker, d.date())
        if res is None:
            break

        if rev_alive:
            if res.get('revenue_beat') == 1:
                rev_streak += 1
            else:
                rev_alive = False

        if eps_alive:
            if res.get('eps_beat') == 1:
                eps_streak += 1
            else:
                eps_alive = False

        if not rev_alive and not eps_alive:
            break   # both streaks ended, no need to look further back

    return {
        'revenue_streak': rev_streak,
        'eps_streak': eps_streak
    }

def get_market_context(as_of_date):
    import yfinance as yf
    import pandas as pd

    try:
        # Use market data strictly before the announcement
        end_date = as_of_date - pd.Timedelta(days=1)
        start_date = end_date - pd.Timedelta(days=5)

        vix = yf.download('^VIX', start=start_date, end=end_date, progress=False)
        oil = yf.download('CL=F', start=start_date, end=end_date, progress=False)

        vix_level = None
        oil_move = None

        if not vix.empty:
            vix_level = round(float(vix['Close'].iloc[-1].item()), 2)

        if not oil.empty and len(oil) >= 2:
            prev = float(oil['Close'].iloc[-2].item())
            curr = float(oil['Close'].iloc[-1].item())
            if prev != 0:
                oil_move = round((curr / prev - 1) * 100, 2)

        return {'vix_level': vix_level, 'oil_move_1d': oil_move}
    except:
        return None
    
def compute_pct_from_52wlow(ticker, as_of_date, df_price):
    if df_price.empty:
        return None

    # Use prices strictly before the announcement
    pre_data = df_price.loc[:pd.Timestamp(as_of_date - timedelta(days=1))]

    if len(pre_data) < 100:   # not enough history
        return None

    df_window = pre_data.tail(260)   # roughly one year of trading days
    high_52w = df_window['close_price'].max()
    low_52w = df_window['close_price'].min()
    current_price = df_window['close_price'].iloc[-1]

    if high_52w == low_52w:
        return None

    pct = ((current_price - low_52w) / (high_52w - low_52w)) * 100
    return round(pct, 2)

def compute_market_cap_features(ticker, as_of_date, df_price):
    """
    Returns:
    {
        'market_cap_bucket': bucket,
        'log_market_cap': log_market_cap
    }
    """
    try:
        stock = yf.Ticker(ticker)
        shares = stock.info.get("sharesOutstanding")
        pre_data = df_price.loc[:pd.Timestamp(as_of_date - timedelta(days=1))]
        close = pre_data.iloc[-1]["close_price"]
        if shares is None or pre_data.empty or pd.isna(close):
            return {
            "market_cap_bucket": None,
            "log_market_cap": None
            }
        market_cap = close * shares
        market_cap_bil = market_cap / 1e9
        if market_cap_bil >= 200:
            bucket = "mega"
        elif market_cap_bil >= 50:
            bucket = "large"
        elif market_cap_bil >= 10:
            bucket = "mid"
        elif market_cap_bil >= 2:
            bucket = "small"
        else:
            bucket = "micro"
        return {
            "market_cap_bucket": bucket,
            "log_market_cap": round(float(np.log1p(market_cap_bil)), 6),
        }
    except Exception:
        return {
            "market_cap_bucket": None,
            "log_market_cap": None
            }
    
def compute_sector_industry(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }
    except Exception:
        return {
            "sector": None,
            "industry": None
        }
    
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
    if df_price.empty:
        return None
    pre_data = df_price.loc[:pd.Timestamp(as_of_date - timedelta(days=1))]

    if pre_data.empty or len(pre_data) < 63:
        return None

    # Current HV20 (from existing function)
    current_vol = compute_volatility_features(as_of_date, df_price)
    if current_vol is None or current_vol.get('volatility_20d') is None:
        return None

    hv20_current = current_vol['volatility_20d']

    # Build historical distribution of HV20
    hv20_history = []
    end_date = as_of_date - timedelta(days=1)
    start_date = end_date - timedelta(days=hist_years * 365)

    lookback_data = pre_data.loc[start_date:end_date]
    if len(lookback_data) < 126:
        return None

    window_start = 0
    close_prices = lookback_data['close_price']
    dates = close_prices.index
    while window_start + 20 <= len(close_prices):   # fixed to <= to capture final window
        window = close_prices.iloc[window_start:window_start + 20]
        returns = window.pct_change().dropna()
        if len(returns) >= 19:
            vol = returns.std() * np.sqrt(252) * 100
            if not pd.isna(vol):
                hv20_history.append(vol)
        window_start += 5

    if len(hv20_history) < 20:
        return None

    hv20_history = np.array(hv20_history)

    percentile = (np.sum(hv20_history < hv20_current) / len(hv20_history)) * 100
    high_vol_regime = 1 if percentile >= 80.0 else 0

    return {
        'hv20_current': round(hv20_current, 2),
        'vol_percentile': round(percentile, 2),
        'high_vol_regime': high_vol_regime
    }
