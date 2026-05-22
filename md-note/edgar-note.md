# EdgarTools Deep‑Dive for Quantitative Finance

A comprehensive, project‑driven guide to extracting SEC filing data with EdgarTools.
All code examples assume you’ve set your identity:

```python
from edgar import set_identity #required
set_identity("Sachio your.email@example.com")
```

## Company 
```python
from edgar import Company

aapl = Company("AAPL")
print(aapl.name)                  # 'APPLE INC'
print(aapl.cik)                   # 320193
print(aapl.sic_code)              # '3571'
print(aapl.sic_description)       # 'Electronic Computers'
print(aapl.shares_outstanding)    # 15115785000.0
print(aapl.public_float)          # 2899948348000.0
```

## fillings
```python
# All filings
filings = Company("MSFT").get_filings()

# Specific form types
tenks = Company("MSFT").get_filings(form="10-K")   # Annual reports
tenqs = Company("MSFT").get_filings(form="10-Q")   # Quarterly reports
eightks = Company("AAPL").get_filings(form="8-K")  # Current events (earnings)
form4s = Company("TSLA").get_filings(form="4")     # Insider trades

# Most recent filings
recent_tenks = tenks.head(5)
latest_filing = filings[0]     

# all of these are still metadata, you need to put .obj() behind it
```

## filling.obj()
```
# 10‑K
tenk = Company("AAPL").get_filings(form="10-K")[0].obj()
print(tenk.business_description[:200])  # Item 1
print(tenk.risk_factors[:200])          # Item 1A
print(tenk.mda[:200])                   # Item 7 – MD&A: Management's Discussion & Analysis.
print(tenk.auditor)                     # AuditorInfo

# Financials from a 10‑K
income = tenk.financials.income_statement()
balance = tenk.financials.balance_sheet()
cashflow = tenk.financials.cash_flow_statement()
```
- Text sections (`.business_description`, `.risk_factors`, `.mda`) → str
- Auditor info → AuditorInfo object
- Financial statements → Statement objects → call `.to_dataframe()` for a DataFrame
- Individual metrics → int (via `.get_value()` or `.get_revenue()`)

## Multi‑Year Financial Statements
```python
financials = Company("MSFT").get_financials()

income = financials.income_statement()
balance = financials.balance_sheet()

# Convert to pandas DataFrame
df = income.to_dataframe()
print(df.columns)   # Period columns + line items
```

## XBRL Facts (Fine‑Grained Metrics)
XBRL (eXtensible Business Reporting Language) is simply the global standard that the SEC requires every public company to use when filing financial reports, built. It turns the raw numbers in a financial statement—like revenue, net income, or total assets—into machine‑readable data.

```python
facts = Company("GOOG").get_facts()

# Common metrics
print(facts.get_revenue())
print(facts.get_net_income())
print(facts.get_total_assets())

# Any XBRL concept
print(facts.get_concept("AccountsPayableCurrent"))

# Time series
revenue_ts = facts.time_series("Revenues")
print(revenue_ts)    # every quarter going back years
```

## Insider Trading
```python
company = Company("NVDA")
form4s = company.get_filings(form="4").head(10)

for f in form4s:
    ownership = f.obj()                    # Form 4 object
    summary = ownership.get_ownership_summary()
    print(f"  Insider: {summary.insider_name}")
    print(f"  Position: {summary.position}")
    print(f"  Activity: {summary.primary_activity}")   # "Purchase" or "Sale"
    print(f"  Net Change: {summary.net_change} shares")
    print(f"  Net Value: ${summary.net_value:,.0f}")

# Convert all transactions to a DataFrame
import pandas as pd
form4s = Company("NVDA").get_filings(form="4").head(20)
txns = pd.concat([f.obj().to_dataframe().fillna('') for f in form4s])
print(txns.head())
```

## 8‑K Earnings Releases & Clean Text
```python
# Latest 8‑K
eightk = Company("TSLA").get_filings(form="8-K").latest().obj()
print(eightk.items)           # reported event types
print(eightk.earnings)        # parsed financial tables (if earnings)

# Clean text for NLP
filing = Company("AAPL").get_filings(form="10-K")[0]
text = filing.text()          # plain text
md = filing.markdown()        # Markdown version
```