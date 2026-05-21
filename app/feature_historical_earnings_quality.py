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

c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

try:
    c.execute("ALTER TABLE features ADD COLUMN hist_gm_change_avg REAL;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN hist_sbc_pct_avg REAL;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN hist_ocf_ni_avg REAL ;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN hist_fcf_quarters INTEGER;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN hist_earnings_quality INTEGER;")
except sqlite3.OperationalError:
    pass   # column already exists

today = date.today()
df_ed = pd.read_sql(
    "SELECT * FROM earnings_calendar WHERE earnings_date > ?",
    conn,
    params=(today.strftime("%Y-%m-%d"),),
    parse_dates='earnings_date'
)

def get_value(df, label, quarter):
    row = df[df['label'] == label]
    return row[quarter].iloc[0] if not row.empty else None


for index,row in df_ed.iterrows(): 
    try:
        ticker = row['ticker']
        ed_clean = row['earnings_date'].date()
        df = pd.read_sql(f"SELECT * FROM price_history WHERE ticker='{ticker}' ORDER BY date", conn, parse_dates='date', index_col='date')

        if df.empty: 
            print(f"no data in {ticker}, skipping...")
            continue

        try:
            gm_list = []
            sbc_list = []
            ocf_list = []
            fcf_pos_count = 0
            company = edgar.Company(ticker)
            facts = company.get_facts()
            cashflow_df = facts.cashflow_statement(periods=4, annual=False, as_dataframe=True)
            income_df = facts.income_statement(periods=20, annual=False, as_dataframe=True)
            for i in range(1, 5):
                latest_q = income_df.columns[i]
                prev_year_q = income_df.columns[i + 4]
                revenue_latest = get_value(income_df, 'Revenues', latest_q)
                cost_of_rev_latest = get_value(income_df, 'CostOfRevenue', latest_q)
                revenue_prev   = get_value(income_df, 'Revenues', prev_year_q)
                cost_of_rev_prev = get_value(income_df, 'CostOfRevenue', prev_year_q)
                ni = get_value(income_df, 'NetIncomeLoss', latest_q)

                ocf = get_value(cashflow_df, 'NetCashProvidedByOperatingActivities', latest_q)
                sbc_annual = None
                sbc_row = income_df[income_df['label'].str.contains('Share.?Based|Stock.?Based|Compensation', case=False, na=False, regex=True)]
                if not sbc_row.empty:
                    # Take the latest quarter value and multiply by 4 to approximate annual
                    sbc_quarterly = sbc_row[latest_q].iloc[0]
                    if pd.notna(sbc_quarterly):
                        sbc_annual = sbc_quarterly * 4

                # --- Capital Expenditures (from cash flow statement) ---
                capex = None
                capex_row = cashflow_df[cashflow_df['label'].str.contains('Capital|PaymentsToAcquireProperty|Equipment', case=False, na=False, regex=True)]
                if not capex_row.empty:
                    capex_quarterly = capex_row[latest_q].iloc[0]
                    if pd.notna(capex_quarterly):
                        capex = capex_quarterly * 4  

                gm_change_bps = None
                sbc_pct = None
                ocf_ni_ratio = None
                fcf_positive = None
                score = None

                if ocf is not None and ni is not None and ni !=0:
                    ocf_ni_ratio = round(ocf/ni, 2)
                    ocf_list.append(ocf_ni_ratio)
                else:
                    ocf_ni_ratio = None

                if all(i is not None for i in [revenue_latest, cost_of_rev_latest, revenue_prev, cost_of_rev_prev]):
                    gm_latest = ((revenue_latest - cost_of_rev_latest)/revenue_latest) * 100
                    gm_prev = ((revenue_prev - cost_of_rev_prev)/revenue_prev) * 100
                    gm_change_bps = round(gm_latest - gm_prev, 2)
                    gm_list.append(gm_change_bps)
                else:
                    gm_change_bps = None
                
                sbc_pct = None
                if sbc_annual and revenue_latest and revenue_latest > 0:
                    sbc_quarterly = sbc_annual / 4
                    sbc_pct = round(sbc_quarterly / revenue_latest * 100, 2)
                    sbc_list.append(sbc_pct)

                if ocf is not None and capex is not None:
                    capex_q = capex / 4
                    fcf = ocf - capex_q
                else:
                    fcf = None
                fcf_positive = 1 if (fcf is not None and fcf > 0) else 0
                if fcf_positive:
                    fcf_pos_count += 1
        except Exception as o:
            print(f"{ticker}: error -> {o}")
            continue
        avg_gm = round(np.mean(gm_list), 2) if gm_list else None
        avg_sbc = round(np.mean(sbc_list), 2) if sbc_list else None
        avg_ocf = round(np.mean(ocf_list), 2) if ocf_list else None

        # Compute score
        score = 3
        if avg_gm is not None and avg_gm < 50:
            score = min(score, 2)
        if avg_sbc is not None and avg_sbc > 3:
            score = min(score, 2)
        if avg_ocf is not None and avg_ocf < 0.8:
            score = 1
        if fcf_pos_count < 2:
            score = 1
        quality = None 
        if score == 3:
            quality = 'High'
        elif score == 2:
            quality = 'Medium'
        else:
            quality = 'Low'
        print(f"{ticker}: Historical earnings quality: {quality}")
    except Exception as e:
        print(f"{ticker}: error -> {e}")
        continue
    if avg_gm is not None:
        c.execute("UPDATE features SET hist_gm_change_avg = ? WHERE ticker = ? AND earnings_date = ?",
        (avg_gm, ticker, ed_clean.strftime("%Y-%m-%d")))
    if avg_sbc is not None:
        c.execute("UPDATE features SET hist_sbc_pct_avg = ? WHERE ticker = ? AND earnings_date = ?",
        (avg_sbc, ticker, ed_clean.strftime("%Y-%m-%d")))
    if avg_ocf is not None:
        c.execute("UPDATE features SET hist_ocf_ni_avg  = ? WHERE ticker = ? AND earnings_date = ?",
        (avg_ocf, ticker, ed_clean.strftime("%Y-%m-%d")))
    if fcf_pos_count is not None:
        c.execute("UPDATE features SET hist_fcf_quarters = ? WHERE ticker = ? AND earnings_date = ?",
            (fcf_pos_count, ticker, ed_clean.strftime("%Y-%m-%d")))
    if score is not None:
        c.execute("UPDATE features SET hist_earnings_quality = ? WHERE ticker = ? AND earnings_date = ?",
            (score, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()