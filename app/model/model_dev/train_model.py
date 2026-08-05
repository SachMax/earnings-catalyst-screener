import sqlite3
import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
import joblib
from sklearn.metrics import roc_auc_score
import warnings
warnings.filterwarnings('ignore')

# ---------------------------------------------------------------------------
# 1. Load data – only rows with features and a target
# ---------------------------------------------------------------------------
conn = sqlite3.connect('data/universe.db')
data = pd.read_sql(
    "SELECT * FROM ml_dataset WHERE quality_curr IS NOT NULL",
    conn,
    parse_dates=['earnings_date'],
    index_col='earnings_date'
)
conn.close()

data = data.dropna(subset=['target_5d_drift'])
drop_sparse = [
    "upward_revision_count60d",
    "downward_revision_count60d",
    "net_revision_count_60d",
    "revision_breadth_60d",
    "estimate_revision_pct",
    "guidance_valid",
    "ticker",
    "log_market_cap",
]

data = data.drop(columns=drop_sparse, errors="ignore")
data['eps_beat_curr'] = data['eps_beat_curr'].replace(-1, np.nan)
data['eps_surprise_pct'] = data['eps_surprise_pct'].replace(-9999.0, np.nan)
data['sue'] = data['sue'].replace(-9999.0, np.nan)

# ---------------------------------------------------------------------------
# 2. Create binary target (up/down)
# ---------------------------------------------------------------------------
y = (data['target_5d_drift'] >= 4).astype(int)       # 1 = up, 0 = down
print(f" y mean = {y.mean()}")
X = data.drop(columns=['target_5d_drift'])
X = X.replace([np.inf, -np.inf], np.nan)

# Feature Engineering
X["trend_regime"] = (
    (X["return_20d"] > 0).astype(int)
    + 2*(X["return_60d"] > 0).astype(int)
)
X["runup_above_history"] = (
    X["runup"] >
    X["hist_runup_avg"]
).astype(int)
X["panic_market"] = (
    (X["vix_level"] > X["vix_level"].quantile(.8)) &
    (X["return_20d"] < X["return_20d"].quantile(.2))
).astype(int)
X["revenue_surprise_proxy"] = (
    X["revenue_latest"] /
    (X["revenue_prev"] + 1e-6)
)

X["market_stress"] = (
    X["volatility_20d"] *
    X["vix_level"]
)
X["oil_sector_interaction"] = (
    X["oil_move_1d"] *
    X["sector_relative_strength"]
)
X["guidance_bert_raise_prob"] = (
    X["guidance_bert_raise_prob"]
        .replace(-1, np.nan)
)
X["guidance_strength"] = pd.cut(
    X["guidance_bert_raise_prob"],
    bins=[0,0.2,0.4,0.6,0.8,1],
    labels=False
)
X["strong_raise"] = (
    X["guidance_bert_raise_prob"] > 0.9
).astype(int)

X["moderate_raise"] = (
    (X["guidance_bert_raise_prob"] > 0.50) &
    (X["guidance_bert_raise_prob"] <= 0.9)
).astype(int)
X["beat_and_strong_guidance"] = (
    (X["eps_surprise_pct"] > 0) &
    (X["guidance_bert_raise_prob"] > 0.8)
).astype(int)
X["surprise_x_guidance"] = (
    X["eps_surprise_pct"] *
    X["guidance_bert_raise_prob"]
)

X = X.drop(columns=['hv20_current'])
cat_cols = X.select_dtypes(include='object').columns.tolist()
num_cols = X.select_dtypes(exclude='object').columns.tolist()
print(f"Cat cols: {len(cat_cols)}, Num cols: {len(num_cols)}")

# ---------------------------------------------------------------------------
# 3. Preprocessing (same as before, all features kept)
# ---------------------------------------------------------------------------
cat_pipe = Pipeline([
    ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
    ('encoder', OneHotEncoder(handle_unknown='ignore', sparse_output=False))
])
num_pipe = Pipeline([
    ('imputer', SimpleImputer(strategy='median', add_indicator=True))
])
preprocessor = ColumnTransformer([
    ('cat', cat_pipe, cat_cols),
    ('num', num_pipe, num_cols)
])

X_pre = preprocessor.fit_transform(X)
feature_names = (
    preprocessor.named_transformers_['cat']
    .named_steps['encoder'].get_feature_names_out(cat_cols).tolist() +
    preprocessor.named_transformers_['num']
    .named_steps['imputer'].get_feature_names_out(num_cols).tolist()
)
X_pre = pd.DataFrame(X_pre, columns=feature_names, index=X.index)
print(f"Full feature set: {len(feature_names)} features")

# ---------------------------------------------------------------------------
# 4. Time‑series split (purged gap=1)
# ---------------------------------------------------------------------------
tscv = TimeSeriesSplit(n_splits=3, gap=1, test_size=len(X_pre)//10)

# ---------------------------------------------------------------------------
# 5. Out‑of‑time split (80% train, 20% test) – used once for each model
# ---------------------------------------------------------------------------
split_idx = int(len(X_pre) * 0.8)
X_train_oot, X_test_oot = X_pre.iloc[:split_idx], X_pre.iloc[split_idx:]
y_train_oot, y_test_oot = y.iloc[:split_idx], y.iloc[split_idx:]

# further split train for early stopping (not needed for RF, kept for consistency)
split = int(len(X_train_oot) * 0.8)
X_tr_oot, X_val_oot = X_train_oot.iloc[:split], X_train_oot.iloc[split:]
y_tr_oot, y_val_oot = y_train_oot.iloc[:split], y_train_oot.iloc[split:]

# ===========================================================================
# 6. Random Forest Classifier
# ===========================================================================
rf_clf = RandomForestClassifier(
    n_estimators=1000,
    max_depth=None,
    min_samples_leaf=15,
    min_samples_split=30,
    random_state=42,
    n_jobs=-1,
)

print("\n=== Random Forest Classifier – Fold Performance ===")
for fold, (train_idx, test_idx) in enumerate(tscv.split(X_pre), 1):
    X_train, X_test = X_pre.iloc[train_idx], X_pre.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    rf_clf.fit(X_train, y_train)
    probas = rf_clf.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, probas)
    print(f"Fold {fold} | AUC: {auc:.3f}")

# Out‑of‑time evaluation
rf_clf.fit(X_train_oot, y_train_oot)
rf_probas = rf_clf.predict_proba(X_test_oot)[:, 1]
print(rf_clf.score(X_test_oot, y_test_oot))
rf_auc = roc_auc_score(y_test_oot, rf_probas)
print(f"OOT ROC AUC: {rf_auc:.3f}")
rf_results = pd.DataFrame({'actual': y_test_oot, 'prob': rf_probas})
rf_results['decile'] = pd.qcut(rf_results['prob'], 10, labels=False)
rf_decile = rf_results.groupby('decile')['actual'].mean()

# ---------------------------------------------------------------------------
# FIXED: actual rankings (continuous target) – align by slicing the original data
# ---------------------------------------------------------------------------
print("\nactual rankings")
# Use the original continuous target, aligned with the test set
y_cont_test_oot = data['target_5d_drift'].iloc[split_idx:]   # same rows as y_test_oot
results = pd.DataFrame({
    "prob": rf_probas,
    "target": y_cont_test_oot.values   # .values to avoid index issues
})
results["decile"] = pd.qcut(results["prob"], 10, labels=False)
print(results.groupby("decile")["target"].mean())

print("\n=== Random Forest Classifier Decile Win Rate (out‑of‑time) ===")
for i in range(10):
    print(f"  Decile {i+1}: {rf_decile.iloc[i]:.3f} ({rf_decile.iloc[i]*100:.1f}%)")
print(f"  Spread (10th - 1st): {rf_decile.iloc[-1] - rf_decile.iloc[0]:.3f}")

top_decile = rf_results[rf_results.decile == 9]["actual"].mean()
bottom_decile = rf_results[rf_results.decile == 0]["actual"].mean()

print("\nTop decile win rate:", top_decile)
print("Bottom decile win rate:", bottom_decile)
print("Lift:", top_decile / y_test_oot.mean())

base_rate = y_test_oot.mean()
top_rate = rf_decile.iloc[-1]
bottom_rate = rf_decile.iloc[0]

print(f"Base rate: {base_rate:.3f}")
print(f"Top lift: {top_rate/base_rate:.2f}x")
print(f"Bottom lift: {bottom_rate/base_rate:.2f}x")

print("\n=== Top 15 Random Forest Feature Importances ===")
importances = pd.Series(rf_clf.feature_importances_, index=feature_names)
top15 = importances.nlargest(15)
for feat, imp in top15.items():
    print(f"  {feat}: {imp:.4f}")

joblib.dump(rf_clf, 'models/rf_classifier.pkl')
joblib.dump(preprocessor, 'models/preprocessor.pkl')
print("Model and preprocessor saved.")