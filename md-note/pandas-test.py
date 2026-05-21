from edgar import Company
import edgar

edgar.set_identity("sachiomaximilliano166@gmail.com")
from edgar import Company
company = Company("BAC")
facts = company.get_facts()
# Search for capex via common XBRL patterns
for concept in facts.list_supported_concepts():
    label = concept.label.lower() if concept.label else ""
    if 'capital' in label or 'capex' in label or 'property' in label:
        print(f"Concept name: {concept.name}, Label: {concept.label}")

for concept in facts.list_supported_concepts():
    label = concept.label.lower() if concept.label else ""
    if 'share' in label or 'compensation' in label or 'sbc' in label:
        print(f"Concept name: {concept.name}, Label: {concept.label}")