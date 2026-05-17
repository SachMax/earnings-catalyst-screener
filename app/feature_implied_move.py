import yfinance as yf
from datetime import date, timedelta
import time
import pandas as pd
import sqlite3

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

try:
    c.execute("ALTER TABLE features ADD COLUMN implied_move REAL")
except sqlite3.OperationalError:
    pass

def get_implied_move (ticker, earnings_date):
    try:
        stock = yf.Ticker(ticker)
        expirations = stock.options
        if not expirations:
            return None
        exp_dates = [i for i in expirations if date.fromisoformat(i) >= earnings_date]
        if not exp_dates:
            return None
        next_exp = exp_dates[0]

        opt_chain = stock.option_chain(next_exp)
        calls = opt_chain.calls
        puts = opt_chain.puts

        current_price = stock.info.get('currentPrice', None) or stock.info.get('regularMarketPrice', None)
        if current_price is None:
            hist = stock.history(period="5d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
        calls['strike_diff'] = abs(calls['strike'] - current_price)
        atm_call = calls.loc[calls['strike_diff'].idxmin()]
        puts['strike_diff'] = abs(puts['strike'] - current_price)
        atm_put = puts.loc[puts['strike_diff'].idxmin()]

        # Mid‑market price of the ATM options
        call_price = (atm_call['bid'] + atm_call['ask']) / 2
        put_price = (atm_put['bid'] + atm_put['ask']) / 2

        # Implied move = (call price + put price) / stock price * 100
        implied_move = (call_price + put_price) / current_price * 100
        return round(implied_move, 2)
    except Exception as e:
        print(f"Error calculating implied move for {ticker}: {e}")
        return None

today = date.today()
df_ed = pd.read_sql("""SELECT * FROM earnings_calendar WHERE earnings_date >= ?""",
                    conn,
                    parse_dates= 'earnings_date',
                    params=(today.strftime("%Y-%m-%d"),))

for index,row in df_ed.iterrows():
    ticker = row['ticker']
    ed_clean = row['earnings_date'].date()
    im = get_implied_move(ticker, ed_clean)
    time.sleep(0.3)
    if im is None:
        print(f"{ticker} -- not enough data")
        continue
    print(f"\n{ticker}: implied move = {im}%")
    c.execute("UPDATE features SET implied_move = ? WHERE ticker = ? AND earnings_date = ?",
          (float(im), ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()
    


