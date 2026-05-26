import edgar 
import  yfinance as yf
import pandas as pd
from datetime import timedelta
import time
edgar.set_identity("sachiomaximilliano166@gmail.com")


jpm = edgar.Company('JPM')
print(jpm.get_quarterly_financials)
