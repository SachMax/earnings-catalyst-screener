import yfinance as yf
ticker = "WMT"
earnings = yf.Ticker(ticker).earnings_dates
print(earnings.columns.tolist())
print(earnings.head(3))