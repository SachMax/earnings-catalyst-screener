import sqlite3
import pandas as pd
from datetime import date, timedelta
import edgar
import logging
logging.getLogger("edgar").setLevel(logging.ERROR)
import numpy as np

edgar.set_identity("sachiomaximilliano166@gmail.com")
conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

# Ensure placeholder rows exist for all upcoming earnings
c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

# Add required historical columns
for col in ['hist_gm_change_avg', 'hist_sbc_pct_avg', 'hist_ocf_ni_avg',
            'hist_fcf_quarters', 'hist_earnings_quality']:
    try:
        c.execute(f"ALTER TABLE features ADD COLUMN {col} {'INTEGER' if 'fcf_quarters' in col or 'quality' in col else 'REAL'}")
    except sqlite3.OperationalError:
        pass

today = date.today()
df_ed = pd.read_sql(
    "SELECT * FROM earnings_calendar WHERE earnings_date > ?",
    conn,
    params=(today.strftime("%Y-%m-%d"),),
    parse_dates='earnings_date'
)

def get_value(df, label, quarter):
    """Safely retrieve a value from the DataFrame, returning None on any error."""
    try:
        row = df[df['label'] == label]
        if not row.empty:
            return row[quarter].iloc[0]
    except (KeyError, IndexError, TypeError):
        pass
    return None

def parse_quarter_key(col):
    """
    Return (year, quarter) for sorting, handling:
    - pandas Period objects
    - strings like 'Q1 2026'
    - strings like '2026Q1'
    """
    if isinstance(col, pd.Period):
        return (col.year, col.quarter)
    s = str(col).strip().upper()
    # Format: 'Q1 2026'
    if ' ' in s and s.startswith('Q'):
        parts = s.split()
        try:
            return (int(parts[1]), int(parts[0][1]))
        except (ValueError, IndexError):
            pass
    # Format: '2026Q1'
    if 'Q' in s and len(s) >= 5 and s[:4].isdigit():
        try:
            return (int(s[:4]), int(s[5]))
        except (ValueError, IndexError):
            pass
    return (0, 0)

for index, row in df_ed.iterrows():
    # Initialize all printed/output variables to prevent NameError
    hist_score = None
    quality = None
    avg_gm = None
    avg_sbc = None
    avg_ocf = None
    fcf_pos_count = None

    try:
        ticker = row['ticker']
        ed_clean = row['earnings_date'].date()

        if ticker == 'TSM':
            print(f"{ticker}: skipping – insufficient quarterly data")
            continue

        try:
            company = edgar.Company(ticker)
            facts = company.get_facts()
            income_df = facts.income_statement(periods=20, annual=False, as_dataframe=True)
            cashflow_df = facts.cashflow_statement(periods=4, annual=False, as_dataframe=True)

            # --- Simple, robust column detection (no regex) ---
            meta_cols = {'label', 'depth', 'is_abstract', 'is_total', 'section', 'confidence'}
            date_cols = [col for col in income_df.columns if col not in meta_cols]
            date_cols.sort(key=parse_quarter_key, reverse=True)

            if len(date_cols) < 9:
                print(f"{ticker}: not enough quarterly columns for historical (need at least 8 quarters), skipping")
                continue

            # Lists to collect raw values across the four quarters
            gm_changes = []
            sbc_pcts = []
            ocf_nis = []
            fcf_positive_quarters = 0

            # Score the four most recent completed quarters (indices 1-4)
            quarterly_scores = []
            for i in range(1, 5):
                try:
                    q_col = date_cols[i]
                    prev_year_col = date_cols[i + 4]
                except IndexError:
                    print(f"  Skipping quarter {i} for {ticker}: column index out of range")
                    quarterly_scores.append(2)
                    continue

                # --- Revenue extraction (multi-label) ---
                revenue_labels = [
                    'Total Revenue', 'Revenues', 'Total net revenues',
                    'Total non-interest revenues', 'Total interest income',
                    'Total revenues', 'Revenue from contracts with customers'
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

                cost_of_rev_latest = get_value(income_df, 'Cost of Revenue', q_col)
                cost_of_rev_prev = get_value(income_df, 'Cost of Revenue', prev_year_col)
                ni = get_value(income_df, 'Net Income (Loss) Attributable to Parent', q_col)

                ocf = get_value(cashflow_df, 'Net Cash Provided by (Used in) Operating Activities', q_col)

                # SBC
                sbc_annual = None
                sbc_row = income_df[income_df['label'].str.contains(
                    'Share.?Based|Stock.?Based|Compensation', case=False, na=False, regex=True)]
                if not sbc_row.empty:
                    try:
                        sbc_q = sbc_row[q_col].iloc[0]
                        if pd.notna(sbc_q):
                            sbc_annual = sbc_q * 4
                    except KeyError:
                        sbc_annual = None

                # Capex
                capex = None
                capex_row = cashflow_df[cashflow_df['label'].str.contains(
                    'Capital|PaymentsToAcquireProperty|Equipment', case=False, na=False, regex=True)]
                if not capex_row.empty:
                    try:
                        capex_q = capex_row[q_col].iloc[0]
                        if pd.notna(capex_q):
                            capex = capex_q * 4
                    except KeyError:
                        capex = None

                # --- Component scoring ---
                components = []

                if all(v is not None for v in [revenue_latest, cost_of_rev_latest, revenue_prev, cost_of_rev_prev]):
                    gm_latest = ((revenue_latest - cost_of_rev_latest) / revenue_latest) * 100
                    gm_prev = ((revenue_prev - cost_of_rev_prev) / revenue_prev) * 100
                    gm_change = round(gm_latest - gm_prev, 2)
                    gm_changes.append(gm_change)
                    if gm_change >= 100:
                        components.append(3)
                    elif gm_change >= 0:
                        components.append(2)
                    else:
                        components.append(1)
                else:
                    components.append(2)

                if sbc_annual is not None and revenue_latest is not None and revenue_latest > 0:
                    sbc_pct = round((sbc_annual / 4) / revenue_latest * 100, 2)
                    sbc_pcts.append(sbc_pct)
                    if sbc_pct < 1.5:
                        components.append(3)
                    elif sbc_pct < 3:
                        components.append(2)
                    else:
                        components.append(1)
                else:
                    components.append(2)

                if ocf is not None and ni is not None and ni != 0:
                    ocf_ni = round(ocf / ni, 2)
                    # Cap extreme values to [-5, 5]
                    ocf_ni = max(-5.0, min(5.0, ocf_ni))
                    ocf_nis.append(ocf_ni)
                    if ocf_ni >= 1.0:
                        components.append(3)
                    elif ocf_ni >= 0.8:
                        components.append(2)
                    else:
                        components.append(1)
                else:
                    components.append(2)

                if capex is not None:
                    capex_qtr = capex / 4
                    fcf = ocf - capex_qtr if ocf is not None else None
                    fcf_pos = 1 if (fcf is not None and fcf > 0) else 0
                    if fcf_pos == 1:
                        components.append(3)
                        fcf_positive_quarters += 1
                    else:
                        components.append(1)
                else:
                    components.append(2)

                q_score = sum(components) / len(components)
                quarterly_scores.append(q_score)

            # After processing the four quarters, compute historical aggregates
            if quarterly_scores:
                avg_score = np.mean(quarterly_scores)

                # Compute averages of raw metrics (if any data was collected)
                avg_gm = round(np.mean(gm_changes), 2) if gm_changes else None
                avg_sbc = round(np.mean(sbc_pcts), 2) if sbc_pcts else None
                avg_ocf = round(np.mean(ocf_nis), 2) if ocf_nis else None
                if avg_ocf is not None and np.isnan(avg_ocf):
                    avg_ocf = None
                fcf_pos_count = fcf_positive_quarters if fcf_positive_quarters > 0 else None

                # --- Data‑sufficiency check ---
                available_components = sum([
                    avg_gm is not None,
                    avg_sbc is not None,
                    avg_ocf is not None,
                    fcf_pos_count is not None
                ])

                if available_components < 2:
                    quality = None
                    hist_score = None
                else:
                    if avg_score >= 2.5:
                        quality = 'High'
                    elif avg_score >= 1.5:
                        quality = 'Medium'
                    else:
                        quality = 'Low'
                    quality_map = {'High': 3, 'Medium': 2, 'Low': 1}
                    hist_score = quality_map[quality]
            else:
                quality = None

        except Exception as o:
            print(f"{ticker}: EDGAR error – {o}")
            continue

        print(f"{ticker}: Historical earnings quality: {quality}")
        print(f"gm change avg ={avg_gm}, sbc avg ={avg_sbc}, ocf/ni avg = {avg_ocf}, fcf pos={fcf_pos_count}")

    except Exception as e:
        print(f"{ticker}: unexpected error – {e}")
        continue

    # Write to DB
    if avg_gm is not None:
        c.execute("UPDATE features SET hist_gm_change_avg = ? WHERE ticker = ? AND earnings_date = ?",
                  (avg_gm, ticker, ed_clean.strftime("%Y-%m-%d")))
    if avg_sbc is not None:
        c.execute("UPDATE features SET hist_sbc_pct_avg = ? WHERE ticker = ? AND earnings_date = ?",
                  (avg_sbc, ticker, ed_clean.strftime("%Y-%m-%d")))
    if avg_ocf is not None:
        c.execute("UPDATE features SET hist_ocf_ni_avg = ? WHERE ticker = ? AND earnings_date = ?",
                  (avg_ocf, ticker, ed_clean.strftime("%Y-%m-%d")))
    if fcf_pos_count is not None:
        c.execute("UPDATE features SET hist_fcf_quarters = ? WHERE ticker = ? AND earnings_date = ?",
                  (fcf_pos_count, ticker, ed_clean.strftime("%Y-%m-%d")))
    if hist_score is not None:
        c.execute("UPDATE features SET hist_earnings_quality = ? WHERE ticker = ? AND earnings_date = ?",
                  (hist_score, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()

conn.close()