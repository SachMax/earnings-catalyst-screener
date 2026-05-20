import edgar

edgar.set_identity("sachiomaximilliano166@gmail.com")

company = edgar.Company("NVDA")
form4s = company.get_filings(form="4").head(10)

for f in form4s:
    ownership = f.obj()
    summary = ownership.get_ownership_summary()
    print(f"  Net Change: {summary.net_change}")
print(summary)