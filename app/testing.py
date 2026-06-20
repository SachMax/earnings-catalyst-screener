# fix_sector_relative_strength.py
import sqlite3
import pandas as pd
from datetime import date, timedelta
from features_library import *

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

# Select all rows that already have features but might have NULL or stale sector relative strength
ml_df = pd.read_sql("""
    SELECT *
    FROM ml_dataset
    WHERE quality_curr IS NOT NULL 
    ORDER BY earnings_date
""", conn, parse_dates=['earnings_date'])

feature_df = pd.read_sql("""
    SELECT * from features order by earnings_date
""", conn, parse_dates=['earnings_date'])

ml_col = ml_df.columns.tolist()
feature_col = feature_df.columns.to_list()

mismatched = set(ml_df.columns) ^ set(feature_df.columns)
print("Mismatched columns:", mismatched)