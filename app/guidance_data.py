# populate_guidance_batch.py
import sqlite3
import pandas as pd
import time
from datetime import date, timedelta
from features_library import load_earnings_dates
import edgar

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BATCH_SIZE = 100000   # rows per run – adjust as needed

# ---------------------------------------------------------------------------
# Helpers (same as before, but you can move them to features_library later)
# ---------------------------------------------------------------------------
def has_item(filing, item_code):
    if filing.items is None:
        return False
    if isinstance(filing.items, str):
        return item_code in filing.items
    return any(item_code in str(it) for it in filing.items)

def extract_guidance_text(ticker, as_of_date):
    """
    Returns (text_snippet, label) where:
        label = 1 : guidance raised
        label = 0 : guidance affirmed / maintained / no clear raise
        label = 2 : no guidance found
    """
    ed_series = load_earnings_dates(ticker)
    past_dates = ed_series[ed_series < pd.Timestamp(as_of_date)]
    if past_dates.empty:
        return "", 2

    prior_date = past_dates.sort_values(ascending=False).iloc[0].date()

    try:
        company = edgar.Company(ticker)
        filings = company.get_filings(form="8-K",
                                      filing_date=f"{prior_date}:{prior_date}")
    except:
        return "", 2

    raise_words = [
        'raise', 'raises', 'raised', 'raising',
        'increase', 'increases', 'increased', 'increasing',
        'boost', 'boosts', 'boosted', 'boosting',
        'upgrade', 'upgrades', 'upgraded', 'upgrading'
    ]
    affirm_words = [
        'affirm', 'affirms', 'affirmed', 'affirming',
        'reaffirm', 'reaffirms', 'reaffirmed', 'reaffirming',
        'reiterate', 'reiterates', 'reiterated', 'reiterating',
        'maintain', 'maintains', 'maintained', 'maintaining',
        'unchanged', 'no change'
    ]

    for f in filings:
        if not has_item(f, '2.02'):
            continue
        try:
            text = f.obj().text()
        except:
            continue

        lower_text = text.lower()
        idx = lower_text.find('guidance')
        if idx == -1:
            continue

        start_idx = max(0, idx - 300)
        end_idx = min(len(lower_text), idx + 500)
        snippet = lower_text[start_idx:end_idx]

        for word in raise_words:
            pos = snippet.find(word)
            if pos != -1 and abs(pos - snippet.find('guidance')) <= 100:
                before_word = snippet[max(0, pos-20):pos]
                if not any(neg in before_word for neg in ['not ', 'no ', 'may not ', 'without ']):
                    return snippet, 1

        for word in affirm_words:
            pos = snippet.find(word)
            if pos != -1 and abs(pos - snippet.find('guidance')) <= 100:
                before_word = snippet[max(0, pos-20):pos]
                if not any(neg in before_word for neg in ['not ', 'no ', 'may not ']):
                    return snippet, 0

        return snippet, 0

    return "", 2

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

# Ensure columns exist (idempotent)
for col in [('text', 'TEXT'), ('label', 'INTEGER')]:
    try:
        c.execute(f"ALTER TABLE guidance_dataset ADD COLUMN {col[0]} {col[1]}")
    except sqlite3.OperationalError:
        pass
conn.commit()

# Select rows that still need population
df = pd.read_sql(f"""
    SELECT ticker, earnings_date
    FROM guidance_dataset
    WHERE text IS NULL
      AND label IS NULL
    ORDER BY earnings_date DESC
    LIMIT {BATCH_SIZE}
""", conn, parse_dates=['earnings_date'])

if df.empty:
    print("No rows to populate. All done!")
    conn.close()
    exit()

print(f"Processing {len(df)} rows...")

for i, (_, row) in enumerate(df.iterrows(), 1):
    ticker = row['ticker']
    ed = row['earnings_date'].date()
    text, label = extract_guidance_text(ticker, ed)
    # Only update if we actually found text (label may be 2, but we still save empty? 
    # We'll save the text snippet and label regardless, because we need to mark the row as processed.
    # If you prefer to leave label=2 rows with NULL text, you can skip, but better to store empty string.)
    c.execute("""
        UPDATE guidance_dataset SET text = ?, label = ?
        WHERE ticker = ? AND earnings_date = ?
    """, (text, label, ticker, ed.strftime('%Y-%m-%d')))
    conn.commit()
    print(f"{ticker} ({ed}): inserted")
    if i % 50 == 0:
        print(f"  Processed {i}/{len(df)} rows...")
    time.sleep(0.05)

conn.close()
print(f"Batch complete. {len(df)} rows updated.")