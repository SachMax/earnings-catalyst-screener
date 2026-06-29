# 📈 Earnings Catalyst Screener

**A leak‑free, NLP‑augmented quantitative pipeline that ranks upcoming earnings events and predicts post‑earnings drift.**

[![Live Dashboard](https://img.shields.io/badge/Live-Dashboard-brightgreen)](https://sachmax-earnings-catalyst-screener.streamlit.app)
[![SSRN Preprint](https://img.shields.io/badge/SSRN-Preprint-blue)](https://papers.ssrn.com/abstract=7009759)

![Dashboard Screenshot](<Screenshot 2026-06-29 170116-1.png>)

---

## 🧠 What It Does

The Earnings Catalyst Screener is a fully automated, production‑grade system that:

- Ingests SEC filings, price history, and analyst data for 200k+ earnings events
- Computes **75+ point‑in‑time features** (fundamentals, technicals, sentiment, volatility, and more)
- Screens upcoming stocks with a **30‑filter rule‑based framework** that assigns conviction levels and trading phases (Phase 2/4/5)
- Uses a **Random Forest classifier** to predict the probability of a significant post‑earnings drift
- Enhances guidance detection with a **fine‑tuned FinBERT model** (F1 0.92) that reads 8‑K filings
- Generates a **daily‑updated dashboard** displaying trade candidates, model predictions, and guidance probabilities

---

## 🚀 Key Features

- ✅ **Leak‑free feature engineering** — every feature is point‑in‑time safe, verified by a manual audit
- ✅ **Phase‑aware screening** — framework distinguishes between pre‑earnings (Phase 2) and post‑earnings (Phase 4) opportunities
- ✅ **NLP‑powered guidance detection** — FinBERT replaces a rule‑based keyword scanner
- ✅ **Fully automated pipeline** — Windows Task Scheduler runs the entire pipeline every morning without manual intervention
- ✅ **Cloud‑connected dashboard** — live Streamlit dashboard backed by a MotherDuck cloud database, refreshed daily
- ✅ **Research‑backed** — documented in a preprint on SSRN with detailed methodology and empirical results

---

## 📊 Performance Highlights

| Metric | Value |
|---|---|
| **Decile Spread** (quality‑filtered) | 30.7 points |
| **Bottom‑Decile Win Rate** | 1.4% |
| **Top‑Decile Win Rate** | 32.1% |
| **FinBERT F1 Score** | 0.92 |
| **Training Data** | 39k+ quality‑filtered events |
| **Guidance Corpus** | 103k+ 8‑K transcripts |

---

## 🖥️ Live Dashboard

👉 [**Launch Dashboard**](https://sachmax-earnings-catalyst-screener.streamlit.app)

The dashboard shows upcoming earnings candidates for the week, grouped by day. Each row includes:

- Predicted win probability (Random Forest)
- Guidance raise probability (FinBERT)
- Phase and conviction from the 30‑filter framework

---

## 📝 Research Paper

A detailed description of the system, feature engineering, model evaluation, and results is available on SSRN:

🔗 [Earnings Catalyst Screener – Preprint](https://papers.ssrn.com/abstract=7009759)

---

## 🛠️ Technology Stack

**Languages:** Python, SQL, batch scripting  
**Machine Learning:** scikit‑learn, XGBoost, Random Forest, PyTorch, HuggingFace Transformers, FinBERT  
**Data Engineering:** pandas, NumPy, yfinance, SEC EDGAR (edgartools), SQLite  
**Automation:** Windows Task Scheduler, custom batch scripts  
**Deployment:** Streamlit, MotherDuck (cloud DuckDB)

---

## 📁 Repository Structure
```
├── app/
│   ├── features_library.py         # Consolidated library of 75+ point‑in‑time feature functions
│   ├── train_model.py              # Model training & evaluation
│   ├── daily_update_features.py    # Refreshes upcoming events
│   ├── historical_feature.py       # Backfills past events for upcoming tickers
│   ├── evaluation_features.py      # 30‑filter rule‑based screening
│   ├── generate_output_dataset.py  # Assembles dashboard data & applies ML model
│   ├── explore_earnings.py         # Refreshes upcoming earnings calendar
│   ├── guidance_*.py               # Guidance model training and backfill scripts
│   ├── populate_features_batch*.py # Incremental historical backfill
│   ├── run_all_features.py         # Orchestrator for live feature table
│   ├── feature_*.py                # Individual feature extractors (20+ scripts)
│   └── dashboard/                  # Streamlit multi‑page dashboard
│       ├── Home.py
│       └── pages/
│           ├── 1_Monday.py
│           ├── 2_Tuesday.py
│           ├── 3_Wednesday.py
│           ├── 4_Thursday.py
│           ├── 5_Friday.py
│           └── 3_Column_Guide.py
├── models/ # Trained model files
├── my_guidance_model/ # FinBERT guidance model
├── my_guidance_tokenizer/ # FinBERT tokenizer
├── run_daily.bat # Daily automation batch file
├── run_quarterly.bat # Quarterly refresh batch file
├── requirements.txt # Python dependencies
└── README.md
```

---

## 📬 Contact

Built by **Sachio Maximilliano Johan**  
📧 sachiomaximilliano166@gmail.com  
🔗 [LinkedIn](https://linkedin.com/in/sachio-maximilliano-johan)   <!-- replace with your real LinkedIn URL -->