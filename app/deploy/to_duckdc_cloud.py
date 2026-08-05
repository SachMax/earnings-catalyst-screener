# sync_to_cloud.py
import sqlite3
import duckdb
import pandas as pd
from config import MOTHERDUCK_KEY

# 1. Read the local output_dataset from SQLite
conn_sqlite = sqlite3.connect("data/universe.db")
df = pd.read_sql("SELECT * FROM output_dataset", conn_sqlite)
conn_sqlite.close()

# 2. Connect to MotherDuck cloud
conn_md = duckdb.connect(f"md:earnings_catalyst?motherduck_token={MOTHERDUCK_KEY}")

# 3. Replace the table in the cloud (if_exists='replace' overwrites it)
conn_md.execute("CREATE OR REPLACE TABLE output_dataset AS SELECT * FROM df")
conn_md.close()

print(f"Synced {len(df)} rows to MotherDuck.")