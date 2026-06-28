# pages/3_Column_Guide.py
import streamlit as st

st.set_page_config(page_title="Column Guide", page_icon="📖")

st.title("📖 Column Guide")
st.caption("What each column in the trade‑candidate table means.")

st.markdown("""
| Column | Description |
|---|---|
| **Ticker** | Stock symbol (e.g., `AAPL`). |
| **Earnings Date** | The date the company is expected to report earnings. |
| **Phase** | Phase assigned by the 30‑filter rule‑based framework. `Phase 2` is a pre‑earnings dip play (rare); `Skip` means the stock didn’t pass the Trifecta gate or was excluded by the run‑up rule. `Phase 4` (post‑earnings pullback) will be added in a future update. |
| **Conviction** | Confidence level of the trade setup, based on the number of passed filters. Possible values: `Very High`, `High`, `Medium`, `Low`. |
| **Position Size (%)** | Recommended capital allocation for a Phase 2 / Phase 4 trade, as determined by the conviction grid and market context (VIX, oil). |
| **Filters Passed** | Number of the 30 filters that the stock passed. |
| **Predicted Win Probability** | Probability (0–1) from the Random Forest classifier that the stock will experience a post‑earnings drift of **+4 % or more** over the following 5 trading days. Colour‑coded: 🟢 > 0.35, 🟠 0.25–0.35, 🔴 < 0.25. |
| **Guidance Raise Probability** | Probability (0–1) from the fine‑tuned FinBERT model that the most recent 8‑K filing contains a guidance raise. `-1.0` means no guidance text was found. Values near 1.0 indicate a clear raise; values near 0.0 indicate no raise language. |
""")

st.info(
    "The dashboard is refreshed daily via an automated pipeline. "
    "The underlying framework is documented in the provided SSRN preprint link."
)

st.divider()
st.markdown(
    "Built by Sachio Maximilliano Johan · "
    "[GitHub](https://github.com/SachMax) · "
    "[SSRN Preprint](https://papers.ssrn.com/abstract=7009759)"
)