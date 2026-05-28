import sqlite3
import pandas as pd
from datetime import date, timedelta
import edgar
import logging
import yfinance as yf
logging.getLogger("edgar").setLevel(logging.ERROR)

edgar.set_identity("sachiomaximilliano166@gmail.com")
conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

# Placeholder rows for upcoming earnings
c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

# Add required columns
for col in ['current_gm_change_bps', 'current_sbc_pct', 'current_ocf_ni_ratio',
            'current_fcf_positive', 'current_earnings_quality', 'revenue_growth_YoY']:
    try:
        c.execute(f"ALTER TABLE features ADD COLUMN {col} {'INTEGER' if 'positive' in col or 'quality' in col or 'YoY' in col else 'REAL'}")
    except sqlite3.OperationalError:
        pass

today = date.today()
df_ed = pd.read_sql("""
    SELECT * FROM earnings_calendar
    WHERE earnings_date > ?
""", conn, params=(today.strftime("%Y-%m-%d"),), parse_dates='earnings_date')

for index, row in df_ed.iterrows():
    # ---- initialize all printed variables to avoid NameError ----
    revenue_latest = None
    revenue_prev = None
    gm_change_bps = None
    sbc_pct = None
    ocf_ni_ratio = None
    fcf_positive = None
    quality = None
    revenue_beat = None
    score = None

    try:
        ticker = row['ticker']
        ed_clean = row['earnings_date'].date()

        try:
            stock = yf.Ticker(ticker)
            income_df = stock.quarterly_financials
            cashflow_df = stock.quarterly_cashflow
            income_df = income_df[sorted(income_df.columns, reverse=True)]
            cashflow_df = cashflow_df[sorted(cashflow_df.columns, reverse=True)]

            if income_df.shape[1] < 5:
                print(f"{ticker}: not enough quarterly data, skipping")
                continue
            
            latest_q = income_df.columns[0]
            prev_year_q = income_df.columns[4]
            # --- Other income statement items (using the now consistent prev_year_q) ---
            revenue_latest = income_df.loc["Total Revenue", latest_q]
            revenue_prev = income_df.loc["Total Revenue", prev_year_q]
            cost_of_rev_latest = income_df.loc["Cost Of Revenue", latest_q] if "Cost Of Revenue" in income_df.index else None
            cost_of_rev_prev  = income_df.loc["Cost Of Revenue", prev_year_q] if "Cost Of Revenue" in income_df.index else None
            ni = income_df.loc["Net Income", latest_q]

            # --- Cash flow items (same period) ---
            # Safely extract cash‑flow items – if a label doesn't exist, leave as None
            ocf = cashflow_df.loc["Operating Cash Flow", latest_q] if "Operating Cash Flow" in cashflow_df.index else None
            try:
                sbc_q = cashflow_df.loc["Stock Based Compensation", latest_q]
            except KeyError:
                sbc_q = None
            try:
                capex = cashflow_df.loc["Capital Expenditure", latest_q]
            except KeyError:
                capex = None

            if ocf is None or sbc_q is None or capex is None:
                try:
                    facts = edgar.Company(ticker).get_facts()
                    cf_df = facts.cashflow_statement(periods=4, annual=False, as_dataframe=True)
                    cf_cols = [c for c in cf_df.columns if c not in ('label', 'depth', 'is_abstract', 'is_total', 'section', 'confidence')]
                    if cf_cols:
                        latest_cf_col = cf_cols[0]
                        if ocf is None:
                            ocf_labels = [
                                "Net Cash Provided by (Used in) Operating Activities",
                                "Net cash (used in) operating activities",
                                "Operating Cash Flow",
                                'NetCashProvidedByUsedInOperatingActivities'
                            ]
                            for lbl in ocf_labels:
                                try:
                                    ocf_test = float(cf_df.loc[lbl, latest_cf_col])
                                    if ocf_test is not None:
                                        ocf = ocf_test
                                        break
                                except (KeyError, IndexError):
                                    continue
                        if capex is None:
                            for lbl in [
                                    "Capital Expenditure",
                                    "Capital Expenditures",
                                    "Payments to Acquire Property, Plant, and Equipment",
                                    "PaymentsToAcquirePropertyPlantAndEquipment",
                                    "CapitalExpendituresIncurredButNotYetPaid"
                                ]:
                                try:
                                    capex = float(cf_df.loc[lbl, latest_cf_col])
                                    break
                                except (KeyError, IndexError):
                                    continue

                        # --- SBC (with per‑label try/except) ---
                        if sbc_q is None:
                            for lbl in ["ShareBasedCompensation",
                                        "Share-based Payment Arrangement, Noncash Expense",
                                        "Share-based Payment Arrangement, Expensed and Capitalized, Amount",
                                        "Stock Based Compensation",
                                        "AllocatedShareBasedCompensationExpense"]:
                                try:
                                    sbc_q = float(cf_df.loc[lbl, latest_cf_col])
                                    break
                                except (KeyError, IndexError):
                                    continue
                except:
                    pass
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
            if capex is not None:
                fcf = ocf + capex if ocf is not None else None
                fcf_positive = 1 if (fcf is not None and fcf > 0) else 0


            # --- Earnings quality score (component-based, v2.9 aligned) ---
            components = []

            # Gross margin change (basis points)
            if gm_change_bps is not None:
                if gm_change_bps >= 100:
                    components.append(3)
                elif gm_change_bps >= 0:
                    components.append(2)
                else:
                    components.append(1)
            else:
                components.append(2)

            # SBC % of revenue (lower is better)
            if sbc_pct is not None:
                if sbc_pct < 1.5:
                    components.append(3)
                elif sbc_pct < 3:
                    components.append(2)
                else:
                    components.append(1)
            else:
                components.append(2)

            # OCF / Net Income ratio
            if ocf_ni_ratio is not None:
                if ocf_ni_ratio >= 1.0:
                    components.append(3)
                elif ocf_ni_ratio >= 0.8:
                    components.append(2)
                else:
                    components.append(1)
            else:
                components.append(2)

            # Free cash flow positivity
            if fcf_positive is not None:
                if fcf_positive == 1:
                    components.append(3)
                else:
                    components.append(1)
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

            # --- Revenue growth (YoY binary proxy) ---
            if revenue_latest is not None and revenue_prev is not None and revenue_prev > 0:
                revenue_beat = 1 if revenue_latest > revenue_prev else 0

        except Exception as o:
            print(f"{ticker}: error – {o}")
            continue

        print(f"{ticker}: Current earnings quality: {quality}")
        print(f"{ticker}: revenue_latest = {revenue_latest}, revenue_prev = {revenue_prev}")
        print(f"gm change={gm_change_bps}, sbc pct={sbc_pct}, ocf/ni={ocf_ni_ratio}, fcf pos={fcf_positive}")
        print(f"revenue_beat = {revenue_beat}")

    except Exception as e:
        print(f"{ticker}: unexpected error – {e}")
        continue

    # --- Write to DB ---
    if gm_change_bps is not None:
        c.execute("UPDATE features SET current_gm_change_bps = ? WHERE ticker = ? AND earnings_date = ?",
                  (gm_change_bps, ticker, ed_clean.strftime("%Y-%m-%d")))
    if sbc_pct is not None:
        c.execute("UPDATE features SET current_sbc_pct = ? WHERE ticker = ? AND earnings_date = ?",
                  (sbc_pct, ticker, ed_clean.strftime("%Y-%m-%d")))
    if ocf_ni_ratio is not None:
        c.execute("UPDATE features SET current_ocf_ni_ratio = ? WHERE ticker = ? AND earnings_date = ?",
                  (ocf_ni_ratio, ticker, ed_clean.strftime("%Y-%m-%d")))
    if fcf_positive is not None:
        c.execute("UPDATE features SET current_fcf_positive = ? WHERE ticker = ? AND earnings_date = ?",
                  (fcf_positive, ticker, ed_clean.strftime("%Y-%m-%d")))
    if score is not None:
        c.execute("UPDATE features SET current_earnings_quality = ? WHERE ticker = ? AND earnings_date = ?",
                  (score, ticker, ed_clean.strftime("%Y-%m-%d")))
    if revenue_beat is not None:
        c.execute("UPDATE features SET revenue_growth_YoY = ? WHERE ticker = ? AND earnings_date = ?",
              (revenue_beat, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()

conn.close()