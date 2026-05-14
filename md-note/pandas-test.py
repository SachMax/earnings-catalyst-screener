import pandas as pd

# Example DataFrame with daily dates
dates = pd.date_range('2024-05-06', periods=10, freq='B')  # business days
df = pd.DataFrame({'close': [150, 151, 152, 153, 154, 155, 156, 157, 158, 159]}, index=dates)
print("Daily data:\n", df)

# Resample to weekly frequency, taking the last close of the week
weekly = df['close'].resample('W').last()
print("\nWeekly (last close of each week):\n", weekly)