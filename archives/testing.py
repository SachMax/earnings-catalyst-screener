import yfinance as yf
import pandas as pd
from datetime import date, timedelta
stock = yf.Ticker("WMT")
today = date.today()
downgrades = stock.upgrades_downgrades
last2weeks = pd.Timestamp(today) - timedelta(days=14)
recent = downgrades[downgrades.index >= last2weeks]
print(recent)