import sqlite3
import pandas as pd
import numpy as np
import joblib
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# 0. Define the output table schema
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 1. Load upcoming events (next 7 days)
# ---------------------------------------------------------------------------
conn = sqlite3.connect('data/universe.db')
c = conn.cursor()
c.execute("DROP TABLE IF EXISTS output_dataset")
c.execute("""
CREATE TABLE output_dataset (
    ticker TEXT,
    earnings_date TEXT,
    phase TEXT,
    conviction TEXT,
    position_size_pct REAL,
    filters_passed INTEGER,
    predicted_win_prob REAL,
    guidance_bert_raise_prob REAL,
    PRIMARY KEY (ticker, earnings_date)
)
""")
conn.commit()

today = date.today()
cutoff = today + timedelta(days=7)

df_upcoming = pd.read_sql("""
    SELECT ticker, earnings_date
    FROM features
    WHERE earnings_date > date('now')
      AND earnings_date <= ?
    ORDER BY earnings_date
""", conn, params=(cutoff.strftime('%Y-%m-%d'),), parse_dates=['earnings_date'])

if df_upcoming.empty:
    print("No upcoming events.")
    conn.close()
    exit()

# ---------------------------------------------------------------------------
# 2. Load saved model and preprocessor
# ---------------------------------------------------------------------------
rf_clf = joblib.load('models/rf_classifier.pkl')
preprocessor = joblib.load('models/preprocessor.pkl')

# ---------------------------------------------------------------------------
# 3. Process each upcoming event (with same feature engineering as training)
# ---------------------------------------------------------------------------
results = []
for _, row in df_upcoming.iterrows():
    ticker = row['ticker']
    ed = row['earnings_date']

    # Get raw features from ml_dataset
    ml_df = pd.read_sql("""
        SELECT * FROM ml_dataset
        WHERE ticker = ? AND earnings_date = ?
    """, conn, params=(ticker, ed.strftime('%Y-%m-%d')))

    if ml_df.empty or ml_df['runup'].isna().iloc[0]:
        continue   # features not yet computed

    # Convert to one-row DataFrame (same columns as training script would load)
    X_row = ml_df.iloc[[0]].copy()

    # Drop identifier/target columns (exactly as in train_model.py)
    drop_cols = [
        'ticker', 'earnings_date', 'target_5d_drift',        # IDs + target
        'upward_revision_count60d', 'downward_revision_count60d',
        'net_revision_count_60d', 'revision_breadth_60d', 'estimate_revision_pct',
        'guidance_valid', 'log_market_cap'                   # sparse / redundant
    ]
    X_row = X_row.drop(columns=[c for c in drop_cols if c in X_row.columns], errors='ignore')

    # Replace sentinel values with NaN (as training does)
    X_row['eps_beat_curr'] = X_row['eps_beat_curr'].replace(-1, np.nan)
    X_row['eps_surprise_pct'] = X_row['eps_surprise_pct'].replace(-9999.0, np.nan)
    X_row['sue'] = X_row['sue'].replace(-9999.0, np.nan)
    X_row = X_row.replace([np.inf, -np.inf], np.nan)

    # After sentinel replacement and before feature engineering
    X_row = X_row.fillna(value=np.nan)
    # -------------------------------------------------------------------
    # Feature engineering (identical to train_model.py)
    # -------------------------------------------------------------------
    X_row["trend_regime"] = (
        (X_row["return_20d"] > 0).astype(int)
        + 2 * (X_row["return_60d"] > 0).astype(int)
    )
    X_row["runup_above_history"] = (
        X_row["runup"] > X_row["hist_runup_avg"]
    ).astype(int)
    X_row["panic_market"] = (
        (X_row["vix_level"] > X_row["vix_level"].quantile(.8)) &
        (X_row["return_20d"] < X_row["return_20d"].quantile(.2))
    ).astype(int)
    X_row["revenue_surprise_proxy"] = (
        X_row["revenue_latest"] / (X_row["revenue_prev"] + 1e-6)
    )
    X_row["market_stress"] = (
        X_row["volatility_20d"] * X_row["vix_level"]
    )
    X_row["oil_sector_interaction"] = (
        X_row["oil_move_1d"] * X_row["sector_relative_strength"]
    )
    # guidance_bert_raise_prob may be NaN after sentinel replacement, keep it
    X_row["guidance_strength"] = pd.cut(
        X_row["guidance_bert_raise_prob"],
        bins=[0, 0.2, 0.4, 0.6, 0.8, 1],
        labels=False
    )
    X_row["strong_raise"] = (
        X_row["guidance_bert_raise_prob"] > 0.9
    ).astype(int)
    X_row["moderate_raise"] = (
        (X_row["guidance_bert_raise_prob"] > 0.50) &
        (X_row["guidance_bert_raise_prob"] <= 0.9)
    ).astype(int)
    X_row["beat_and_strong_guidance"] = (
        (X_row["eps_surprise_pct"] > 0) &
        (X_row["guidance_bert_raise_prob"] > 0.8)
    ).astype(int)
    X_row["surprise_x_guidance"] = (
        X_row["eps_surprise_pct"] * X_row["guidance_bert_raise_prob"]
    )

    # Drop hv20_current (as training does)
    X_row = X_row.drop(columns=['hv20_current'], errors='ignore')

    # -------------------------------------------------------------------
    # Preprocess & predict
    # -------------------------------------------------------------------
    X_pre = preprocessor.transform(X_row)
    win_prob = rf_clf.predict_proba(X_pre)[0][1]

    # -------------------------------------------------------------------
    # Get rule‑based evaluation from features table
    # -------------------------------------------------------------------
    eval_df = pd.read_sql("""
        SELECT phase, conviction, position_size_pct, filters_passed
        FROM features
        WHERE ticker = ? AND earnings_date = ?
    """, conn, params=(ticker, ed.strftime('%Y-%m-%d')))

    phase = eval_df['phase'].iloc[0] if not eval_df.empty else None
    conviction = eval_df['conviction'].iloc[0] if not eval_df.empty else None
    position_size = eval_df['position_size_pct'].iloc[0] if not eval_df.empty else None
    filters_passed = eval_df['filters_passed'].iloc[0] if not eval_df.empty else None

    # Guidance probability from the row
    guidance_prob = X_row['guidance_bert_raise_prob'].iloc[0]

    results.append({
        'ticker': ticker,
        'earnings_date': ed.strftime('%Y-%m-%d'),
        'phase': phase,
        'conviction': conviction,
        'position_size_pct': position_size,
        'filters_passed': filters_passed,
        'predicted_win_prob': win_prob,
        'guidance_bert_raise_prob': guidance_prob if not pd.isna(guidance_prob) else None
    })

# ---------------------------------------------------------------------------
# 4. Replace the contents of output_dataset
# ---------------------------------------------------------------------------
c.execute("DELETE FROM output_dataset")
conn.commit()

for entry in results:
    c.execute("""
        INSERT OR REPLACE INTO output_dataset
        (ticker, earnings_date, phase, conviction, position_size_pct, filters_passed,
        predicted_win_prob, guidance_bert_raise_prob)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        entry['ticker'], entry['earnings_date'], entry['phase'], entry['conviction'],
        f"{entry['position_size_pct']}%", int(entry['filters_passed']),
        round(entry['predicted_win_prob'], 2),
        round(entry['guidance_bert_raise_prob'], 4) if entry['guidance_bert_raise_prob'] is not None else None
    ))
conn.commit()

conn.close()
print(f"output_dataset updated with {len(results)} rows.")