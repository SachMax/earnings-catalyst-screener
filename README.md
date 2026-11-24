# 📈 Earnings Catalyst Screener

**An NLP-augmented quantitative research pipeline that screens upcoming earnings events and estimates post-earnings drift.**

[![Live Dashboard](https://img.shields.io/badge/Live-Dashboard-brightgreen)](https://sachmax-earnings-catalyst-screener.streamlit.app)

![Dashboard Screenshot](<Screenshot 2026-06-29 170116-1.png>)

---

## 🧠 What It Does

The Earnings Catalyst Screener is an end-to-end quantitative research system designed to:

- Ingest SEC filings, price history, and analyst data for **200k+ historical earnings events**
- Compute **75+ engineered features** across fundamentals, technicals, sentiment, volatility, and market context
- Screen upcoming stocks with a **30-filter rule-based framework** that evaluates conviction and trading phases
- Use a **Random Forest classifier** in the deployed prediction pipeline to estimate the probability of significant post-earnings drift
- Enhance guidance detection with a **fine-tuned FinBERT model** (previously reported F1: **0.92**) that analyzes earnings-related filings and text
- Generate a **Streamlit dashboard** displaying upcoming earnings candidates, model predictions, and guidance probabilities

---

## Key Features

- **Historical feature engineering** — incorporates event-specific financial and market information; point-in-time availability and leakage controls are being audited and improved
- **Phase-aware screening** — combines a rule-based earnings framework with market, technical, and fundamental filters; the current live evaluation script focuses on **Phase 2** candidates
- **NLP-powered guidance detection** — fine-tuned FinBERT supplements rule-based analysis of management guidance
- **Automated data pipeline** — Python and Windows Task Scheduler support recurring price, calendar, feature, evaluation, and cloud-sync jobs
- **Cloud-connected dashboard** — Streamlit reads published screening results from **MotherDuck** (cloud DuckDB); automatic refresh depends on the scheduled pipeline running successfully
- **C++ trading engine** — separate C++17/CMake component for portfolio positions, trade history, and realized P&L, under development

---

## 📊 Performance Highlights

| Metric | Value |
|---|---|
| **Decile Spread** (quality-filtered, earlier experiment) | 30.7 points |
| **Bottom-Decile Win Rate** (earlier experiment) | 1.4% |
| **Top-Decile Win Rate** (earlier experiment) | 32.1% |
| **FinBERT F1 Score** (previous experiment) | 0.92 |
| **Training Data** (earlier quality-filtered sample) | 39k+ events |
| **Guidance Corpus** | 103k+ filing/transcript records |

*The results above describe earlier research runs, not independently verified live-trading performance. Model validation and historical feature auditing are ongoing; these figures should not be interpreted as investment returns.*

---

## 🖥️ Live Dashboard

👉 [**Launch Dashboard**](https://sachmax-earnings-catalyst-screener.streamlit.app)

The dashboard is designed to show upcoming earnings candidates for the week, grouped by day. Each row includes:

- Predicted win probability (Random Forest)
- Guidance raise probability (FinBERT)
- Phase and conviction from the rule-based screening framework

The first dashboard version has been deployed. **Scheduled updates are being restored following a project restructure**, so displayed data may not currently be fresh.

---

## 🛠️ Technology Stack

**Languages:** Python, SQL, C++17, batch scripting  
**Machine Learning:** scikit-learn, CatBoost, XGBoost, Random Forest, PyTorch, Hugging Face Transformers, FinBERT  
**Data Engineering:** pandas, NumPy, yfinance, SEC EDGAR (edgartools), SQLite  
**Automation:** Windows Task Scheduler, custom batch scripts  
**Deployment:** Streamlit, MotherDuck (cloud DuckDB)  
**C++ Development:** STL, CMake

---

## 📁 Repository Structure

```text
├── app/
│   ├── config.py                       # Application and service configuration
│   ├── features_library.py             # Shared feature engineering library
│   ├── features_library_corrected.py   # Revised feature-library version
│   ├── data_pipeline/
│   │   ├── explore_earnings.py          # Refreshes upcoming earnings calendar
│   │   ├── daily_update_features.py    # Updates features for upcoming events
│   │   ├── update_price_history.py     # Updates historical market prices
│   │   ├── fetch_price_history.py      # Historical price ingestion
│   │   └── historical_earnings_date.py  # Historical earnings-date utilities
│   ├── features/                      # Individual feature extractors (20+ scripts)
│   │   ├── feature_current_earnings_quality.py
│   │   ├── feature_historical_earnings_quality.py
│   │   ├── feature_analyst_revision.py
│   │   ├── feature_sector_relative_strength.py
│   │   ├── feature_sue.py
│   │   └── feature_*.py
│   ├── guidance/                      # FinBERT / guidance data and model scripts
│   │   ├── guidance_model.py
│   │   ├── guidance_model_ml_dataset.py
│   │   ├── guidance_data_asc.py
│   │   └── guidance_*.py
│   ├── model/
│   │   └── model_dev/
│   │       ├── train_model.py          # Model training and evaluation
│   │       └── build_targets.py        # Target construction
│   ├── deploy/
│   │   ├── run_all_features.py         # Orchestrates feature extractors
│   │   ├── evaluation_features.py      # Rule-based earnings screening
│   │   ├── generate_output_dataset.py  # Generates dashboard predictions
│   │   └── to_duckdc_cloud.py          # Publishes output to MotherDuck
│   ├── historical_feature.py          # Incremental history for upcoming tickers
│   ├── populate_features_batch_desc.py # Historical feature backfill
│   └── dashboard/                     # Streamlit multipage dashboard
│       ├── home.py
│       └── pages/
│           ├── 1_Monday.py
│           ├── 2_Tuesday.py
│           ├── 3_Wednesday.py
│           ├── 4_Thursday.py
│           ├── 5_Friday.py
│           └── Column_Guide.py
├── artifacts/
│   ├── models/
│   │   ├── rf_classifier.pkl          # Random Forest classifier used by v1
│   │   ├── preprocessor.pkl           # Saved preprocessing pipeline
│   │   ├── catboost_classifier.pkl    # Research model artifact
│   │   ├── rf_classifier_top80.pkl
│   │   └── rf_regressor.pkl
│   ├── my_guidance_model/             # Fine-tuned FinBERT weights/config
│   └── my_guidance_tokenizer/         # FinBERT tokenizer files
├── automation_scripts/
│   ├── run_daily.bat                  # Daily pipeline
│   └── run_quarterly.bat              # Periodic maintenance / refresh
├── engine/                            # C++17 trading/portfolio engine
│   ├── apps/
│   ├── include/
│   ├── src/
│   └── CMakeLists.txt
├── data/                              # Local datasets and SQLite database
├── tests/                             # Tests
├── requirements.txt                   # Python dependencies
└── README.md
```

*Some local data, trained artifacts, and environment files may be excluded from Git tracking because of their size or sensitivity.*

---

## 📬 Contact

Built by **Sachio Maximilliano Johan**  
📧 sachiomaximilliano166@gmail.com  
🔗 [LinkedIn](https://linkedin.com/in/sachio-maximilliano-johan)