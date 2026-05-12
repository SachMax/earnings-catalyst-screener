# yfinance – Python Library for Yahoo Finance Data

## What is yfinance?
`yfinance` is a free Python library that lets you download historical market data, fundamental information, and earnings dates from Yahoo Finance. It's the main tool your Earnings Catalyst Screener will use to fetch all stock‑related data.

## Installation
```bash
pip install yfinance
```
## How it works
```python
import yfinance as yf

# Create a Ticker object for PepsiCo
pep = yf.Ticker("PEP")
 ```
 Once you have a Ticker, you can ask it for different kinds of data:
- Price history – daily open/high/low/close/volume

- Fundamental info – sector, market cap, P/E ratio, etc.

- Earnings dates – historical and upcoming earnings announcements

- Financial statements – quarterly/annual balance sheet, income, cash flow

### Price History
The most important method for your project. It returns a pandas DataFrame.
``` python
# Get the last 5 days of data
hist = pep.history(period="5d")

# Get exactly 1 year of data
hist = pep.history(period="1y")

# Get data between two exact dates
hist = pep.history(start="2024-01-01", end="2024-12-31")

# Get all available data
hist = pep.history(period="max")
```

Columns returned (daily): Open, High, Low, Close, Volume, Dividends, Stock Splits.

Basic useful commands:
``` 
print(hist.head())             # first 5 rows
print(hist['Close'].mean())    # average closing price
print(hist['Close'].iloc[-1])  # most recent close
```

### Fundamental Data
pep.info is a dictionary with hundreds of fields. The most useful ones for your filters:
``` python
info = pep.info
print(info['sector'])          # e.g. 'Consumer Defensive'
print(info['marketCap'])       # market capitalisation
print(info['trailingPE'])      # price‑to‑earnings ratio
print(info['shortPercentOfFloat']) # short interest (Filter 16)
print(info['recommendationKey'])   # analyst consensus (e.g. 'buy')
print(info['numberOfAnalystOpinions'])
```
### Earning Dates
Returns a DataFrame with past and future earnings dates, EPS estimates, and reported EPS.
```python
ed = pep.earnings_dates
print(ed.head())
```
`earnings_dates` may be empty for some tickers or during certain periods. Always check if it's None or empty before using it.

### Other Useful Methods
| Method | What it returns |
| :--- | :--- |
| `pep.quarterly_financials` | Quarterly income statement, balance sheet, cash flow | 
| `pep.balance_sheet` | Annual balance sheet | 
| `pep.cashflow` | Annual cash flow | 
| `pep.recommendations` | 	Analyst upgrade/downgrade history |
| `pep.options` | 	Expiration dates for options (for Filter 12) |

### Working with Multiple Tickers
You'll often loop through a list of tickers:
```python
tickers = ["PEP", "TSM", "GS", "AAPL"]
for t in tickers:
    stock = yf.Ticker(t)
    hist = stock.history(period="5y")
    # store hist in your database 
```
**Warning**: Calling yfinance inside a tight loop can be slow and may get rate‑limited. For your S&P 500 pipeline, you'll use the download() function (covered later) to pull many tickers at once

## Common Pitfalls & Tips
- Empty data: If a ticker is invalid, history() returns an empty DataFrame. Always check with hist.empty.

- Rate limits: Yahoo Finance may temporarily - block too many rapid requests. Use time.sleep(0.5) between calls when pulling hundreds of tickers.

- Missing fields: Not all stocks have the same info keys. Use info.get('key', 'N/A') to avoid KeyErrors.

- Time zone: Price history uses the exchange's time zone (US stocks = Eastern Time). Keep this in mind when checking earnings dates.