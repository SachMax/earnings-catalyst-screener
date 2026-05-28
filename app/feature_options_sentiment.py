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
    c.execute("ALTER TABLE features ADD COLUMN call_put_volume_ratio REAL")
except sqlite3.OperationalError:
    pass

try:
    c.execute("ALTER TABLE features ADD COLUMN put_call_price_skew REAL")
except sqlite3.OperationalError:
    pass

today = date.today()
df_ed = pd.read_sql("""SELECT * FROM earnings_calendar WHERE earnings_date >= ?""",
                    conn,
                    parse_dates= 'earnings_date',
                    params=(today.strftime("%Y-%m-%d"),))

for index,row in df_ed.iterrows():
    ticker = row['ticker']
    ed_clean = row['earnings_date'].date()
    try: 
        stock = yf.Ticker(ticker)
        expirations = stock.options
        if not expirations:
            continue
        exp_dates = [i for i in expirations if date.fromisoformat(i) >= ed_clean]
        if not exp_dates:
            continue
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

        call_vol = atm_call.get('volume', 0)
        put_vol = atm_put.get('volume', 0)
        call_ask = atm_call.get('ask', None)
        put_ask = atm_put.get('ask', None)
        call_put_vol = None
        if call_vol > 0 and put_vol > 0:
            call_put_vol = round(call_vol / put_vol, 2)

        # Compute price skew (default to None)
        put_call_skew = None
        if call_ask is not None and put_ask is not None and call_ask > 0 and put_ask > 0:
            put_call_skew = round(put_ask / call_ask, 2)
    except Exception as e:
        print(f"{ticker}: error -> {e}")
        continue
    time.sleep(0.3)
    print(f"{ticker}: call/put volume ration = {call_put_vol}")
    print(f"{ticker}: put/call skew ratio = {put_call_skew}")
    if call_put_vol > 1.5:
        print("Bullish")
    elif 1.0 < call_put_vol <= 1.5:
        print("Neutral")
    else:
        print("Bearish")

    if put_call_skew is not None:
        if put_call_skew <= 1.5:
            print("Pass\n")
        elif 1.5 < put_call_skew <= 2.0:
            print("Reduce conviction\n")
        else:
            print("Skip trade\n")
    else:
        print("Skew data unavailable\n")
    c.execute("UPDATE features SET call_put_volume_ratio = ? WHERE ticker = ? AND earnings_date = ?",
          (float(call_put_vol), ticker, ed_clean.strftime("%Y-%m-%d")))
    c.execute("UPDATE features SET put_call_price_skew = ? WHERE ticker = ? AND earnings_date = ?",
          (float(put_call_skew), ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()
    


