import sqlite3
import pandas as pd

# 1. Read PEP data from your database
conn = sqlite3.connect('data/universe.db')
df = pd.read_sql(
    "SELECT * FROM price_history WHERE ticker='PEP'",
    conn,
    index_col='date',
    parse_dates='date'
)
conn.close()

# 2. Ensure data is sorted by date (important for time-series)
df.sort_index(inplace=True)

# 3. Compute daily price change
delta = df['close_price'].diff()

# 4. Separate gains and losses
gain = delta.clip(lower=0)    # keep only positive changes
loss = -delta.clip(upper=0)   # keep only negative changes (as positive values)

# 5. Compute 14-day average gain and average loss
avg_gain = gain.rolling(window=14).mean()
avg_loss = loss.rolling(window=14).mean()

# 6. Calculate RSI = 100 - (100 / (1 + RS))  where RS = avg_gain / avg_loss
rs = avg_gain / avg_loss
rsi = 100.0 - (100.0 / (1.0 + rs))

# 7. Combine with close price and view the last 20 rows
df['RSI'] = rsi
print(df[['close_price', 'RSI']].tail(20))