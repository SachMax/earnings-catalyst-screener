import sqlite3

conn = sqlite3.connect('data/universe.db')
conn.execute("PRAGMA busy_timeout = 5000")
c = conn.cursor()

c.execute("PRAGMA table_info(ml_dataset)")
all_columns = [row[1] for row in c.fetchall()]
keep = {'ticker', 'earnings_date', 'target_5d_drift'}
null_cols = [col for col in all_columns if col not in keep]

if null_cols:
    set_clause = ', '.join(f"{col} = NULL" for col in null_cols)
    c.execute(f"UPDATE ml_dataset SET {set_clause}")
    conn.commit()
    print(f"Reset {len(null_cols)} feature columns to NULL for all rows.")

conn.close()