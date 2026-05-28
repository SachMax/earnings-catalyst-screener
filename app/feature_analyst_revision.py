import sqlite3
import pandas as pd
import yfinance as yf
from datetime import date, timedelta

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

try:
    c.execute("ALTER TABLE features ADD COLUMN upward_revision_count_60d INTEGER;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN downward_revision_count_60d INTEGER;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN net_revision_count_60d INTEGER;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN revision_breadth_60d REAL;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN revision_trend_label TEXT;")
except sqlite3.OperationalError:
    pass   # column already exists
try:
    c.execute("ALTER TABLE features ADD COLUMN estimate_revision_pct REAL;")
except sqlite3.OperationalError:
    pass   # column already exists

today = date.today()
df_ed = pd.read_sql(
    "SELECT * FROM earnings_calendar WHERE earnings_date > ?",
    conn,
    params=(today.strftime("%Y-%m-%d"),),
    parse_dates='earnings_date'
)

def rating_tier(grade):
    grade_lower = str(grade).lower()
    if grade_lower in ['buy','overweight','outperform']:
        return 2   # bullish
    elif grade_lower in ['hold','neutral','market perform','sector perform']:
        return 1   # neutral
    elif grade_lower in ['sell','underperform','underweight']:
        return 0   # bearish
    return 1  # unknown -> treat as neutral

for index,row in df_ed.iterrows(): 
    try:
        ticker = row['ticker']
        ed_clean = row['earnings_date'].date()

        try:
            stock = yf.Ticker(ticker)
            downgrades = stock.upgrades_downgrades
            last60days = pd.Timestamp(today) - timedelta(days=60)
            recent = downgrades[downgrades.index >= last60days]
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

        except Exception as o:
            print(f"{ticker}: error -> {o}")
            continue
        print(f"{ticker}: Analyst revision trend = {label} with revision pct = {revision_pct}")
    except Exception as e:
        print(f"{ticker}: error -> {e}")
        continue
    if upgrade_count is not None:
        c.execute("UPDATE features SET upward_revision_count_60d = ? WHERE ticker = ? AND earnings_date = ?",
        (upgrade_count, ticker, ed_clean.strftime("%Y-%m-%d")))
    if downgrade_count is not None:
        c.execute("UPDATE features SET downward_revision_count_60d = ? WHERE ticker = ? AND earnings_date = ?",
        (downgrade_count, ticker, ed_clean.strftime("%Y-%m-%d")))
    if net_revision_count_60d is not None:
        c.execute("UPDATE features SET net_revision_count_60d  = ? WHERE ticker = ? AND earnings_date = ?",
        (net_revision_count_60d, ticker, ed_clean.strftime("%Y-%m-%d")))
    if breadth is not None:
        c.execute("UPDATE features SET revision_breadth_60d = ? WHERE ticker = ? AND earnings_date = ?",
            (breadth, ticker, ed_clean.strftime("%Y-%m-%d")))
    if label is not None:
        c.execute("UPDATE features SET revision_trend_label = ? WHERE ticker = ? AND earnings_date = ?",
            (label, ticker, ed_clean.strftime("%Y-%m-%d")))
    if revision_pct is not None:
        c.execute("UPDATE features SET estimate_revision_pct = ? WHERE ticker = ? AND earnings_date = ?",
            (revision_pct, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()