import edgar

edgar.set_identity("sachiomximilliano166@gmail.com")

eightk = edgar.Company("TSLA").get_filings(form="8-K").latest()
print(eightk.items)           # reported event types
print(eightk.earnings) 
print(eightk)
