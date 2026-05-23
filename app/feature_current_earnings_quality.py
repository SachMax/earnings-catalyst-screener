import sqlite3
import pandas as pd
from datetime import date, timedelta
import edgar
import logging
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
            'current_fcf_positive', 'current_earnings_quality', 'revenue_growth_YoY', 'revenue_beat']:
    try:
        c.execute(f"ALTER TABLE features ADD COLUMN {col} {'INTEGER' if 'positive' in col or 'quality' in col or 'YoY' in col else 'REAL'}")
    except sqlite3.OperationalError:
        pass

today = date.today()
df_ed = pd.read_sql("""
    SELECT * FROM earnings_calendar
    WHERE earnings_date > ?
""", conn, params=(today.strftime("%Y-%m-%d"),), parse_dates='earnings_date')

def get_value(df, label, quarter):
    row = df[df['label'] == label]
    return row[quarter].iloc[0] if not row.empty else None

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

        if ticker == 'TSM':
            print(f"{ticker}: skipping – insufficient quarterly data")
            continue

        try:
            company = edgar.Company(ticker)
            facts = company.get_facts()
            income_df = facts.income_statement(periods=20, annual=False, as_dataframe=True)
            cashflow_df = facts.cashflow_statement(periods=4, annual=False, as_dataframe=True)

            # --- Simple, robust column detection ---
            meta_cols = {'label', 'depth', 'is_abstract', 'is_total', 'section', 'confidence'}
            date_cols = [col for col in income_df.columns if col not in meta_cols]
            if len(date_cols) < 5:
                print(f"{ticker}: not enough quarterly columns, skipping")
                continue

            latest_q = date_cols[0]
            prev_year_q = date_cols[4]   # will be overwritten if revenue uses a different quarter

            # --- Revenue search (multi-label, walk back up to 4 quarters) ---
            revenue_labels = [
                'Total Revenue', 'Revenues', 'Total net revenues',
                'Total non-interest revenues', 'Total interest income',
                'Total revenues', 'Revenue from contracts with customers'
            ]

            revenue_latest = None
            revenue_prev = None
            latest_q_used = None

            for lbl in revenue_labels:
                for col in date_cols[:4]:
                    val = get_value(income_df, lbl, col)
                    if val is not None and pd.notna(val):
                        revenue_latest = val
                        latest_q_used = col
                        break
                if revenue_latest is not None:
                    break

            # Get same quarter a year earlier for revenue
            if revenue_latest is not None and latest_q_used is not None:
                idx = date_cols.index(latest_q_used)
                if idx + 4 < len(date_cols):
                    prev_year_q = date_cols[idx + 4]          # use the consistent quarter for everything
                    revenue_prev = get_value(income_df, lbl, prev_year_q)
                    if revenue_prev is None or pd.isna(revenue_prev):
                        revenue_prev = None

            # --- Other income statement items (using the now consistent prev_year_q) ---
            cost_of_rev_latest = get_value(income_df, 'Cost of Revenue', latest_q)
            cost_of_rev_prev = get_value(income_df, 'Cost of Revenue', prev_year_q)
            ni = get_value(income_df, 'Net Income (Loss) Attributable to Parent', latest_q)

            # --- Cash flow items (same period) ---
            ocf = get_value(cashflow_df, 'Net Cash Provided by (Used in) Operating Activities', latest_q)

            # SBC
            sbc_annual = None
            sbc_row = income_df[income_df['label'].str.contains(
                'Share.?Based|Stock.?Based|Compensation', case=False, na=False, regex=True)]
            if not sbc_row.empty:
                sbc_q = sbc_row[latest_q].iloc[0]
                if pd.notna(sbc_q):
                    sbc_annual = sbc_q * 4

            # Capex
            capex = None
            capex_row = cashflow_df[cashflow_df['label'].str.contains(
                'Capital|PaymentsToAcquireProperty|Equipment', case=False, na=False, regex=True)]
            if not capex_row.empty:
                capex_q = capex_row[latest_q].iloc[0]
                if pd.notna(capex_q):
                    capex = capex_q * 4

            # Derived metrics
            gm_change_bps = None
            if all(v is not None for v in [revenue_latest, cost_of_rev_latest, revenue_prev, cost_of_rev_prev]):
                gm_latest = ((revenue_latest - cost_of_rev_latest) / revenue_latest) * 100
                gm_prev = ((revenue_prev - cost_of_rev_prev) / revenue_prev) * 100
                gm_change_bps = round(gm_latest - gm_prev, 2)

            sbc_pct = None
            if sbc_annual is not None and revenue_latest is not None and revenue_latest > 0:
                sbc_pct = round((sbc_annual / 4) / revenue_latest * 100, 2)

            ocf_ni_ratio = None
            if ocf is not None and ni is not None and ni != 0:
                ocf_ni_ratio = round(ocf / ni, 2)

            fcf_positive = None
            if capex is not None:
                capex_q = capex / 4
                fcf = ocf - capex_q if ocf is not None else None
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
            print(f"{ticker}: EDGAR error – {o}")
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
    c.execute("UPDATE features SET revenue_beat = NULL WHERE ticker = ? AND earnings_date = ?",
              (ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()

conn.close()