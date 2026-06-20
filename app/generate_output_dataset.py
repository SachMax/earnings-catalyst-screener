# generate_output_dataset.py
import sqlite3
import pandas as pd
import joblib
from datetime import date, timedelta
from features_library import *   # if you need to recompute any feature
# You'll also need the same preprocessing as in train_model.py

# ---------------------------------------------------------------------------
# 1. Load upcoming events (next 7 days)
# ---------------------------------------------------------------------------
conn = sqlite3.connect('data/universe.db')
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
# 3. For each upcoming event, get features from ml_dataset
#    (assuming daily_update_features.py already populated them)
# ---------------------------------------------------------------------------
results = []
for _, row in df_upcoming.iterrows():
    ticker = row['ticker']
    ed = row['earnings_date']

    # Get features from ml_dataset for this (ticker, date)
    ml_df = pd.read_sql("""
        SELECT * FROM ml_dataset
        WHERE ticker = ? AND earnings_date = ?
    """, conn, params=(ticker, ed.strftime('%Y-%m-%d')))

    if ml_df.empty or ml_df['runup'].isna().iloc[0]:
        continue   # features not yet computed

    # Drop columns that are not features
    X_row = ml_df.drop(columns=['ticker', 'earnings_date', 'target_5d_drift'], errors='ignore')
    
    # Apply the same preprocessing as during training
    X_pre = preprocessor.transform(X_row)
    
    # Predict win probability (probability of class 1 = up)
    win_prob = rf_clf.predict_proba(X_pre)[0][1]
    
    # Also get the rule-based evaluation from features table
    eval_df = pd.read_sql("""
        SELECT phase, conviction, position_size_pct, filters_passed
        FROM features
        WHERE ticker = ? AND earnings_date = ?
    """, conn, params=(ticker, ed.strftime('%Y-%m-%d')))
    
    phase = eval_df['phase'].iloc[0] if not eval_df.empty else None
    conviction = eval_df['conviction'].iloc[0] if not eval_df.empty else None
    position_size = eval_df['position_size_pct'].iloc[0] if not eval_df.empty else None
    filters_passed = eval_df['filters_passed'].iloc[0] if not eval_df.empty else None
    
    results.append({
        'ticker': ticker,
        'earnings_date': ed.strftime('%Y-%m-%d'),
        'phase': phase,
        'conviction': conviction,
        'position_size_pct': position_size,
        'filters_passed': filters_passed,
        'predicted_win_prob': win_prob,
        'predicted_drift': None,   # could add regressor later
        'guidance_bert_raise_prob': None,  # placeholder for FinBERT
        'runup': X_row['runup'].iloc[0] if 'runup' in X_row.columns else None,
        'rsi': X_row['rsi'].iloc[0] if 'rsi' in X_row.columns else None,
        'sector_relative_strength': X_row['sector_relative_strength'].iloc[0] if 'sector_relative_strength' in X_row.columns else None,
        'last_updated': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    })

# ---------------------------------------------------------------------------
# 4. Write (or replace) output_dataset
# ---------------------------------------------------------------------------
output_df = pd.DataFrame(results)
output_df.to_sql('output_dataset', conn, if_exists='replace', index=False)
conn.commit()
conn.close()
print(f"Output dataset created with {len(output_df)} rows.")