from app.features_library import *
import pandas as pd
from datetime import date, timedelta

ticker = "ORCL"
ed = date.today()  # or use a specific upcoming date
df_price = load_price_history(ticker)
rel = compute_sector_relative_strength(ticker, ed, df_price)
print(rel)