# audit_column_null.py
import sqlite3
import pandas as pd

conn = sqlite3.connect('data/universe.db')

# Get all column names from ml_dataset
c = conn.cursor()
c.execute("PRAGMA table_info(ml_dataset)")
cols = [row[1] for row in c.fetchall()]

# Skip identifier/target columns (adjust if you want them included)
skip_cols = {'ticker', 'earnings_date', 'target_5d_drift'}
feature_cols = [col for col in cols if col not in skip_cols]

# ----- 1. Fill rate across ALL rows (with a target) -----
print("Fill rate across all rows with a drift target:")
print(f"{'Column':<35} {'Total non-NULL':>15} {'Pct':>8}")
print("-" * 60)

for col in feature_cols:
    total = c.execute(f"SELECT COUNT(*) FROM ml_dataset WHERE target_5d_drift IS NOT NULL").fetchone()[0]
    non_null = c.execute(f"SELECT COUNT(*) FROM ml_dataset WHERE target_5d_drift IS NOT NULL AND {col} IS NOT NULL").fetchone()[0]
    pct = (non_null / total * 100) if total > 0 else 0
    # Print only if fill rate is below some threshold, e.g., 10%, to avoid spam
    if pct < 10:
        print(f"{col:<35} {non_null:>15,}   {pct:5.1f}%")

print()

# ----- 2. Fill rate among rows that already have fundamental features (quality_curr) -----
print("Fill rate among rows with quality_curr IS NOT NULL:")
print(f"{'Column':<35} {'Total non-NULL':>15} {'Pct':>8}")
print("-" * 60)

for col in feature_cols:
    total_quality = c.execute(f"SELECT COUNT(*) FROM ml_dataset WHERE quality_curr IS NOT NULL").fetchone()[0]
    non_null = c.execute(f"SELECT COUNT(*) FROM ml_dataset WHERE quality_curr IS NOT NULL AND {col} IS NOT NULL").fetchone()[0]
    pct = (non_null / total_quality * 100) if total_quality > 0 else 0
    if pct < 10:
        print(f"{col:<35} {non_null:>15,}   {pct:5.1f}%")

conn.close()