# Pandas Deep‑Dive for Quantitative Finance

A practical, project‑driven curriculum covering 90% of the pandas you'll need for the Earnings Catalyst Screener.  
Work through each block by typing the code yourself in a playground file (e.g., `playground_pandas.py`).

---

## Block 1: Core Operations 

### 1.1 DataFrame & Series
- **DataFrame** = table (rows × columns).  
- **Series** = single column.  
- **Index** = row labels; **Columns** = column labels.

```python
import pandas as pd
import numpy as np

dates = pd.date_range('2026-05-01', periods=3)
df = pd.DataFrame({
    'PEP': [151.0, 152.5, 153.2],
    'TSM': [400.0, 398.5, 397.3],
    'GS':  [940.0, 945.0, 950.0]
}, index=dates)
print(df)
```

### 1.2 Selecting & Filtering
- `df['PEP']` → Series
- `df[['PEP', 'TSM']]` → DataFrame (double brackets)
- Filter rows: `df[df['PEP'] > 152]`
- Combine: `df.loc[df['GS'] > 942, 'PEP']` → PEP values where GS > 942

### 1.3 Adding / Modifying Columns
- New column: `df['AAPL']` = [290.0, 292.0, 291.5]
- Derived column: `df['PEP_return'] = df['PEP'].pct_change()`
$$pct = (price~after - price~before)/price~after$$

### 1.4 Reading & Writing CSV
``` python
df.to_csv('data/my_data.csv') #save .csv file
df_loaded = pd.read_csv('data/my_data.csv', index_col=0, parse_dates=True) # load .csv file
```

## Block 2: Data Wrangling & Time Series 

### 2.1 Handling Missing Data
- Drop rows: `df.dropna()` Remove rows with missing data (`NaN`).
- Fill: `df.fillna(method='ffill')` (forward‑fill: Each NaN takes the value from the previous row).

Your price data from yfinance rarely has gaps, but when you merge datasets later, missing values appear.

### 2.2 Grouping & Aggregation
Example:
| ticker | date       | close  |
| :----- | :--------- | :----- |
| PEP    | 2024‑05‑10 | 153.2  |
| PEP    | 2024‑05‑11 | 154.1  |
| PEP    | 2024‑05‑12 | 152.8  |
| TSM    | 2024‑05‑10 | 366.0  |
| TSM    | 2024‑05‑11 | 364.5  |
| TSM    | 2024‑05‑12 | 370.2  |

`df.groupby('ticker')['close'].mean()`-> Output:

| ticker | close  |
| :----- | :----- |
| PEP    | 153.37 |
| TSM    | 366.90 |

`.agg()` - multiple statistics at once \
= `df.groupby('ticker')['close'].agg(['mean', 'std', 'count'])`

### 2.3 Merging / Joining
Example:
- Table A: daily price data (ticker, date, close).
- Table B: sector information (ticker, sector).

You want to attach the sector to each row of the price table. \
`pd.merge(left, right, on='ticker', how='left')`
- left = first DataFrame (the main one you want to keep).
- right = second DataFrame (the lookup table).
- on='ticker' = the column that exists in both, used to match rows.
- how='left' = keep all rows from the left table, and bring in matching values from the right. If a ticker in left doesn’t appear in right, the new columns get NaN.

###  2.4 Time‑Series Resampling & Shifting
`.shift(1)` – **look back one row** \
`df['close'].shift(1)` creates a new column where each value is the previous day’s close. The first row gets NaN because there’s nothing before it.

`.resample('W')` – **change the frequency** \
Changes the frequency of your time‑series data – daily → weekly, weekly → monthly, etc. You must set the date column as the index first.

``` python
df.set_index('date', inplace=True)
weekly_close = df['close'].resample('W').last()   # last price of each week
monthly_avg = df['close'].resample('ME').mean()    # monthly average
```
Example: 
| date       | close  |
| :--------- | :----- |
| 2024‑05‑06 | 150  |
| 2024‑05‑07 | 151  |
| 2024‑05‑08 | 152  |
| 2024‑05‑09 | 153  |
| 2024‑05‑10 | 154  |
| 2024‑05‑13 | 156  |
| 2024‑05‑14 | 157  |
| 2024‑05‑15 | 158  |
| 2024‑05‑16 | 159  |
| 2024‑05‑17 | 160  |

```python
import pandas as pd

# Example DataFrame with daily dates
dates = pd.date_range('2024-05-06', periods=10, freq='B')  # business days
df = pd.DataFrame({'close': [150, 151, 152, 153, 154, 155, 156, 157, 158, 159]}, index=dates)
print("Daily data:\n", df)

# Resample to weekly frequency, taking the last close of the week
weekly = df['close'].resample('W').last()
print("\nWeekly (last close of each week):\n", weekly)
```

| date       | close  |
| :--------- | :----- |
| 2024‑05‑12 | 154  |
| 2024‑05‑19 | 160  |

## Block 3: Advanced & Quant‑Specific
### 3.1 Vectorized Operations (Avoid Loops!)
```python
import pandas as pd
import numpy as np

# Create a Series of daily returns (e.g., from a stock)
returns = pd.Series([0.01, 0.02, -0.005, 0.03, -0.01])  # example

# Cumulative return: (1+r1)*(1+r2)*... - 1
cumulative_return = (1 + returns).cumprod() - 1
print(cumulative_return)
```

### 3.2 Rolling Windows
What it does: It takes a window of a fixed size (e.g., 20 days) and slides it across your data, applying a function (like mean() or std()) to each window. This is how you compute moving averages, rolling volatility, and similar metrics.

```python
df['close'].rolling(window=20).mean() #→ 20‑day moving average.

df['close'].rolling(20).std() #→ rolling volatility (20‑day).
```

Example:
```python 
# df_long is a DataFrame with columns: ticker, date, close
df_long.set_index('date', inplace=True)

# Compute 5-day rolling mean of close for each ticker
rolling_means = df_long.groupby('ticker')['close'].rolling(5).mean()
print(rolling_means)
```

### 3.3 Custom Functions with .apply()
for example:
```python
import pandas as pd

df = pd.DataFrame({'close': [100, 150, 200]})

# Multiply every close price by 1.1 (add 10%)
df['close_up'] = df['close'].apply(lambda x: x * 1.1)
print(df)
```
Output 
```text
   close  close_up
0    100     110.0
1    150     165.0
2    200     220.0
```

Another example:
```python
df = pd.DataFrame({
    'close': [150.0, 366.0],
    'volume': [4500000, 8900000]
})

df['close_per_vol'] = df.apply(lambda row: row['close'] / row['volume'], axis=1)
print(df)
```
Output
```text
   close   volume  close_per_vol
0   150.0  4500000    3.333333e-05
1   366.0  8900000    4.112360e-05
```
- axis=0 (default) → passes each column (as a Series) to the function.
- axis=1 → passes each row (as a Series) to the function.

#### The Fastest Vectorized Way: `np.where`
```python
import numpy as np

df['tsm_category'] = np.where(df['close'] > 400, 'above 400', 'below 400')
``` 
If condition is True, pick x; otherwise pick y.

## Useful Pandas Function

- `ed_clean = pd.Timestamp(ed).date()` \
to convert into a python datetime object

- `close_14d_before = df.loc[date_14d_before, 'close_price']` \
to locate and print out the close_price with certain date

- ```python
    idx_14d = df.index.get_indexer([date_14d_before], method='ffill')[0]
    used_14d = df.index[idx_14d].date()
    close_14d_before = df.iloc[idx_14d]['close_price'] 
  ```
  - `idx_14d = df.index.get_indexer([date_14d_before], method='ffill')[0]`\
  to get the index for that certain date, if it doesnt have that date, then it will take the nearest index that has a date (backwards)
  - `used_14d = df.index[idx_14d].date()` \
  to get the date of that index
  - close_14d_before = df.iloc[idx_14d]['close_price'] \
  to get the close_price based on the index 