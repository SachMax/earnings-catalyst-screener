import sqlite3
import pandas as pd

# 1. Read PEP data from your database
conn = sqlite3.connect('data/universe.db')
df = pd.read_sql("SELECT * FROM price_history WHERE ticker='PEP'", conn)

df['date'] = pd.to_datetime(df['date'])   # convert strings to datetime
df.sort_values('date', inplace=True)      # sort oldest → newest
df.set_index('date', inplace=True)        # make date the row labels

delta = df['close_price'].diff()

gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)

avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()

RS = avg_gain/avg_loss
RSI = 100 - (100 / (1 + RS))
df['RSI'] = RSI 
print(df.tail(20))

conn.close()