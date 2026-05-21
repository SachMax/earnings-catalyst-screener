import yfinance as yf
from datetime import date, timedelta
import pandas as pd

ticker = "RL"

try:
    stock = yf.Ticker(ticker)
    cal = stock.calendar
    # Get the next earnings date and convert to a date object
    ed_raw = cal['Earnings Date'][0]
    ed_clean = pd.Timestamp(ed_raw).date()

    # Find the first options expiration on or after the earnings date
    expirations = stock.options
    exp_dates = [d for d in expirations if date.fromisoformat(d) >= ed_clean]
    if not exp_dates:
        print("No options expiry covering the earnings event.")
        exit()
    next_exp = exp_dates[0]

    # Get the options chain for that expiry
    opt_chain = stock.option_chain(next_exp)
    calls = opt_chain.calls
    puts = opt_chain.puts

    # Current stock price
    current_price = stock.info.get('currentPrice') or stock.info.get('regularMarketPrice')
    if current_price is None:
        hist = stock.history(period="5d")
        if not hist.empty:
            current_price = hist['Close'].iloc[-1]
    if current_price is None:
        print("Could not fetch current price.")
        exit()

    # ATM strike selection
    calls['strike_diff'] = abs(calls['strike'] - current_price)
    atm_call = calls.loc[calls['strike_diff'].idxmin()]
    puts['strike_diff'] = abs(puts['strike'] - current_price)
    atm_put = puts.loc[puts['strike_diff'].idxmin()]

    # Mid-market prices (for implied move – not used here but nice to have)
    call_price = (atm_call['bid'] + atm_call['ask']) / 2
    put_price = (atm_put['bid'] + atm_put['ask']) / 2

    # --- Options Sentiment ---
    call_vol = atm_call.get('volume', 0)
    put_vol = atm_put.get('volume', 0)
    call_ask = atm_call.get('ask', None)
    put_ask = atm_put.get('ask', None)

    # Call/Put Volume Ratio
    call_put_vol = None
    if call_vol > 0 and put_vol > 0:
        call_put_vol = round(call_vol / put_vol, 2)

    # Put-Call Price Skew
    put_call_skew = None
    if call_ask is not None and put_ask is not None and call_ask > 0 and put_ask > 0:
        put_call_skew = round(put_ask / call_ask, 2)

    # --- Output ---
    print(f"Ticker: {ticker}")
    print(f"Next earnings date: {ed_clean}")
    print(f"Options expiry used: {next_exp}")
    print(f"Current price: ${current_price:.2f}")
    print(f"ATM Call (strike ${atm_call['strike']:.0f}): bid ${atm_call['bid']:.2f}, ask ${atm_call['ask']:.2f}")
    print(f"ATM Put  (strike ${atm_put['strike']:.0f}): bid ${atm_put['bid']:.2f}, ask ${atm_put['ask']:.2f}")
    print(f"Call/Put Volume Ratio: {call_put_vol}")
    print(f"Put/Call Price Skew: {put_call_skew}")

    # Interpretation
    if call_put_vol is not None:
        if call_put_vol > 1.5:
            print("Volume Ratio interpretation: Bullish")
        elif 1.0 < call_put_vol <= 1.5:
            print("Volume Ratio interpretation: Neutral")
        else:
            print("Volume Ratio interpretation: Bearish")

    if put_call_skew is not None:
        if put_call_skew <= 1.5:
            print("Skew interpretation: Pass")
        elif 1.5 < put_call_skew <= 2.0:
            print("Skew interpretation: Reduce conviction")
        else:
            print("Skew interpretation: Skip trade")

except Exception as e:
    print(f"Error: {e}")