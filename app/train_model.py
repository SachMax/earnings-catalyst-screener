from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestRegressor
import pandas as pd
import sqlite3

conn = sqlite3.connect('data/universe.db')
data = pd.read_sql("SELECT * FROM ml_dataset", conn,
                    parse_dates=['earnings_date'], index_col='earnings_date')

# Encode categorical columns
cols_to_encode = ['scs_conviction_penalty', 'past_earnings_action', 'past_pullback_bounce']
encoder = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
enc_vals = encoder.fit_transform(data[cols_to_encode])
new_cols = encoder.get_feature_names_out(cols_to_encode)
enc_df = pd.DataFrame(enc_vals, columns=new_cols, index=data.index)

data = data.drop(columns=cols_to_encode)
data = pd.concat([data, enc_df], axis=1)

# Now loop over unique tickers
for ticker in data['ticker'].unique():
    ticker_data = data[data['ticker'] == ticker]
    if len(ticker_data) < 12:   # skip tickers with too little data
        continue

    exclude_cols = ['ticker', 'target_5d_drift']
    X = ticker_data.drop(columns=exclude_cols, errors='ignore')
    y = ticker_data['target_5d_drift']

    # Remove any rows with NaN in X or y
    mask = X.notna().all(axis=1) & y.notna()
    X, y = X[mask], y[mask]

    if len(X) < 12:
        continue

    tscv = TimeSeriesSplit(n_splits=3, gap=1, test_size=8)
    for train_idx, test_idx in tscv.split(X, y):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        reg = RandomForestRegressor(n_estimators=100, random_state=42)
        reg.fit(X_train, y_train)
        score = reg.score(X_test, y_test)
        print(f"{ticker} | Fold score: {score:.3f}")


