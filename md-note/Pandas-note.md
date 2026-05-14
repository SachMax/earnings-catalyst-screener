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
| 2024‑05‑15 |   |
| 2024‑05‑16 | 370.2  |
| 2024‑05‑17 | 366.0  |
