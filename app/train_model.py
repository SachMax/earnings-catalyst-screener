import sqlite3
import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
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
data = data.drop(columns=['ticker'], errors='ignore')

# ---------------------------------------------------------------------------
# 2. Create binary target (up/down)
# ---------------------------------------------------------------------------
target = 'target_5d_drift'
y = (data[target] > 0).astype(int)          # 1 = up, 0 = down
X = data.drop(columns=[target])

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

# further split train for early stopping (XGBoost)
split = int(len(X_train_oot) * 0.8)
X_tr_oot, X_val_oot = X_train_oot.iloc[:split], X_train_oot.iloc[split:]
y_tr_oot, y_val_oot = y_train_oot.iloc[:split], y_train_oot.iloc[split:]

# ===========================================================================
# 6. Random Forest Classifier
# ===========================================================================
rf_clf = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    min_samples_leaf=5,
    min_samples_split=10,
    max_features='sqrt',
    random_state=42,
    n_jobs=-1
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
rf_results = pd.DataFrame({'actual': y_test_oot, 'prob': rf_probas})
rf_results['decile'] = pd.qcut(rf_results['prob'], 10, labels=False)
rf_decile = rf_results.groupby('decile')['actual'].mean()

print("\n=== Random Forest Classifier Decile Win Rate (out‑of‑time) ===")

for i in range(10):
    print(f"  Decile {i+1}: {rf_decile.iloc[i]:.3f} ({rf_decile.iloc[i]*100:.1f}%)")
print(f"  Spread (10th - 1st): {rf_decile.iloc[-1] - rf_decile.iloc[0]:.3f}")
print("\n=== Top 15 Random Forest Feature Importances ===")
importances = pd.Series(rf_clf.feature_importances_, index=feature_names)
top15 = importances.nlargest(15)
for feat, imp in top15.items():
    print(f"  {feat}: {imp:.4f}")