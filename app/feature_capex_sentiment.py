import sqlite3
import pandas as pd
from datetime import date, timedelta
import yfinance as yf
import time

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

try:
    c.execute("ALTER TABLE features ADD COLUMN scs_market_punishing_capex INTEGER;")
except sqlite3.OperationalError:
    pass   # column already exists

try:
    c.execute("ALTER TABLE features ADD COLUMN scs_monetisation_evidence INTEGER;")
except sqlite3.OperationalError:
    pass   # column already exists

try:
    c.execute("ALTER TABLE features ADD COLUMN scs_conviction_penalty TEXT;")
except sqlite3.OperationalError:
    pass   # column already exists

try:
    c.execute("ALTER TABLE features ADD COLUMN scs_capex_trigger_active INTEGER;")
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
        df = pd.read_sql(f"SELECT * FROM price_history WHERE ticker='{ticker}' ORDER BY date", conn, parse_dates='date', index_col='date')

        if df.empty: 
            print(f"no data in {ticker}, skipping...")
            continue
        market_punishing_val = None
        monetisation = None
        conviction_penalty = None
        capex_trigger_active = None

        try:
            c.execute("SELECT sector FROM features WHERE ticker = ? and earnings_date = ?", (ticker, ed_clean.strftime("%Y-%m-%d")))
            irow = c.fetchone()
            if irow is None:
                print(f"{ticker}: no sector data")
                continue
            sector = irow[0]
            if sector is None or sector != "Technology":
                print(f"{ticker}: not Technology (sector = {sector}), skipping SCS")
                continue
        except Exception as p:
            print(f"{ticker}: error -> {p}")
            continue
        try:
            c.execute("SELECT sector_relative_strength FROM features WHERE ticker = ? and earnings_date = ?", (ticker, ed_clean.strftime("%Y-%m-%d")))
            erow = c.fetchone()
            if erow is None:
                print(f"{ticker}: no sector relative strength data")
                continue
            sector_rel_str = erow[0]
            if sector_rel_str is None:
                print(f"{ticker}: sector relative strength not found")
                continue
        except Exception as l:
            print(f"{ticker}: error -> {l}")
            continue
        try:
            etf_data = yf.download('XLK', period='5d', progress=False)
            time.sleep(0.5)
            if len(etf_data) < 2:
                print(f"{ticker}: not enough trading data, skipping")
                continue

            etf_data_start    = etf_data['Close'].iloc[0]
            etf_data_end      = etf_data['Close'].iloc[-1]

            # Percentage returns
            etf_return    = ((etf_data_end - etf_data_start) / etf_data_start) * 100
            print(f"\n{ticker}:etf return = {etf_return}")
        except Exception as o:
            print(f"{ticker}: error -> {o}")
            continue

        try:
            stock = yf.Ticker(ticker)
            downgrades = stock.upgrades_downgrades
            last2weeks = pd.Timestamp(today) - timedelta(days=14)
            recent = downgrades[downgrades.index >= last2weeks]
            time.sleep(0.5)
            downgrade_count = 0
            for _, rrow in recent.iterrows():
                grade_from = rating_tier(rrow.get('FromGrade', ''))
                grade_to = rating_tier(rrow.get('ToGrade', ''))
                if grade_to < grade_from:
                    downgrade_count += 1
            print(f"{ticker}:downgrades count = {downgrade_count}\n")
            market_punishing_val = 0
            if etf_return < -3.00 and downgrade_count >= 2:
                market_punishing_val = 1 #TRUE since its negative
            else:
                market_punishing_val = 0
            print(f"{ticker}: punished = {market_punishing_val}\n")
        except Exception as op:
            print(f"{ticker}: error -> {op}")
            continue

        try:
            capex = stock.info.get('capitalExpenditures')
            revGrowth = stock.info.get('revenueGrowth')
            revenue = stock.info.get('totalRevenue')
            downgrades = stock.upgrades_downgrades
            monetisation = 0
            if revGrowth is not None and revGrowth > 0.20:
                monetisation = 1
            elif capex is not None and revenue is not None and revenue > 0:
                capex_ratio = capex / revenue
                if capex_ratio < 0.05:  
                    monetisation = 1
            print(f"{ticker}:monetisation = {monetisation}\n")
        except Exception as op:
            print(f"{ticker}: error -> {op}")
            continue
        conviction_penalty = None
        if market_punishing_val == 1 and monetisation == 0:
            if etf_return < -5.0 and revGrowth < 0:
                conviction_penalty = 'Skip'
            else:
                conviction_penalty = "Reduce"
        else:
            conviction_penalty = "None"
        print(f"{ticker}:conviction penalty = {conviction_penalty}\n")
        capex_trigger_active = 1 if conviction_penalty in ('Reduce', 'Skip') else 0
        print(f"{ticker}:capex trigger active = {capex_trigger_active}\n")
    except Exception as e:
        print(f"{ticker}: error -> {e}")
        continue
    c.execute("UPDATE features SET scs_market_punishing_capex = ? WHERE ticker = ? AND earnings_date = ?",
          (market_punishing_val, ticker, ed_clean.strftime("%Y-%m-%d")))
    c.execute("UPDATE features SET scs_monetisation_evidence = ? WHERE ticker = ? AND earnings_date = ?",
          (monetisation, ticker, ed_clean.strftime("%Y-%m-%d")))
    c.execute("UPDATE features SET scs_conviction_penalty = ? WHERE ticker = ? AND earnings_date = ?",
          (conviction_penalty, ticker, ed_clean.strftime("%Y-%m-%d")))
    c.execute("UPDATE features SET scs_capex_trigger_active = ? WHERE ticker = ? AND earnings_date = ?",
          (capex_trigger_active, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()