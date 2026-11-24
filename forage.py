from sklearn.model_selection import TimeSeriesSplit
from sklearn.linear_model import LinearRegression
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

data_df = pd.read_csv("C:/Users/Sachio/Downloads/Nat_Gas (1).csv", index_col="Dates", parse_dates=["Dates"])
plt.plot(data_df.index, data_df["Prices"], label="Natural Gas Price")
data_df["t"] = np.arange(len(data_df))
data_df["sin"] = np.sin(((np.pi)/6)*data_df['t'])
data_df["cos"] = np.cos(((np.pi)/6)*data_df['t'])

y = data_df['Prices']
X = data_df.drop(columns=['Prices'])

tssp = TimeSeriesSplit(n_splits=3)

model = LinearRegression()

for fold, (train_idx, test_idx) in enumerate(tssp.split(X), 1):
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
    print(f"fold {fold} r2: {score}")

model.fit(X,y)
print("Intercept:", model.intercept_)
print("Coefficients:", model.coef_)

predictions = model.predict(X)

print("test 1")
def future_estimation (date):
    start_date = data_df.index.min()
    date = pd.to_datetime(date)
    t_val = (
        (date.year - start_date.year)*12 + (date.month - start_date.month)
    )
    sin_val = np.sin(((np.pi)/6)*t_val)
    cos_val = np.cos(((np.pi)/6)*t_val)
    instance = pd.DataFrame({
    "t": [t_val],
    "sin": [sin_val],
    "cos": [cos_val]
    })
    return model.predict(instance)[0]

print("test 2")
def contract_value(
    dates,
    injection_dates,
    withdrawal_dates,
    prices,
    injection_rate,
    withdrawal_rate,
    max_storage,
    storage_cost
):
    storage = 0.0
    value = 0.0

    injection_dates = set(injection_dates)
    withdrawal_dates = set(withdrawal_dates)

    for d in dates:
        price = prices[d]
        if price is None:
            price = future_estimation(d)
        
        # 1. Inject gas
        if d in injection_dates:
            inject_volume = min(injection_rate, max_storage - storage)
            storage += inject_volume
            value -= inject_volume * price

        # 2. Withdraw gas
        if d in withdrawal_dates:
            withdraw_volume = min(withdrawal_rate, storage)
            storage -= withdraw_volume
            value += withdraw_volume * price
        

        # 3. Storage cost
        value -= storage_cost * storage

    return value

print("test 3")
    
dates = [
    "2024-01-01",
    "2024-02-01",
    "2024-03-01",
    "2024-04-01"
]

prices = {
    "2024-01-01": 10,
    "2024-02-01": 12,
    "2024-03-01": 15,
    "2024-04-01": 18
}

injection_dates = ["2024-01-01", "2024-02-01"]
withdrawal_dates = ["2024-03-01", "2024-04-01"]

print(
    contract_value(
        dates=dates,
        injection_dates=injection_dates,
        withdrawal_dates=withdrawal_dates,
        prices=prices,
        injection_rate=100,
        withdrawal_rate=100,
        max_storage=200,
        storage_cost=0.1
    )
)
    
plt.plot(data_df.index, y, label="Actual")
plt.plot(data_df.index, predictions, label="Fitted")
plt.show()