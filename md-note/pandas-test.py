from edgar import Company
import edgar

edgar.set_identity("sachiomaximilliano166@gmail.com")
from edgar import Company
company = edgar.Company("GS")
income = company.get_financials().income_statement().to_dataframe()
print(income[income['label'].str.contains('Revenue|Interest income', case=False, na=False)]['label'].unique())