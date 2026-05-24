import sqlite3
import pandas as pd
from datetime import date, timedelta
import edgar
import yfinance as yf
import time

edgar.set_identity("sachiomaximilliano166@gmail.com")

conn = sqlite3.connect('data/universe.db')
c = conn.cursor()

# Ensure placeholder rows exist
c.execute("""
    INSERT OR IGNORE INTO features (ticker, earnings_date)
    SELECT ticker, earnings_date FROM earnings_calendar
    WHERE earnings_date > date('now')
""")
conn.commit()

# Add guidance_valid column if not present
try:
    c.execute("ALTER TABLE features ADD COLUMN guidance_valid INTEGER;")
except sqlite3.OperationalError:
    pass

today = date.today()
df_ed = pd.read_sql(
    "SELECT * FROM earnings_calendar WHERE earnings_date > ?",
    conn,
    params=(today.strftime("%Y-%m-%d"),),
    parse_dates='earnings_date'
)

def has_item(filing, item_code):
    """Return True if the filing contains the given item code."""
    if filing.items is None:
        return False
    if isinstance(filing.items, str):
        return item_code in filing.items
    return any(item_code in str(it) for it in filing.items)

for index, row in df_ed.iterrows():
    ticker = row['ticker']
    ed_clean = row['earnings_date'].date()

    guidance_valid = None

    try:
        stock = yf.Ticker(ticker)
        earnings_hist = stock.earnings_dates
        if earnings_hist is None or earnings_hist.empty:
            print(f"{ticker}: no earnings history from yfinance")
            continue

        reported = earnings_hist[earnings_hist['Reported EPS'].notna()]
        if reported.empty:
            print(f"{ticker}: no reported earnings dates")
            continue

        last_report_date = reported.index[0].date()
        print(f"{ticker}: last reported earnings was {last_report_date}")

        start = last_report_date - timedelta(days=4)
        end   = last_report_date + timedelta(days=4)
        company = edgar.Company(ticker)
        filings = company.get_filings(form="8-K", filing_date=f"{start}:{end}")
        time.sleep(0.3)
    except Exception as e:
        print(f"{ticker}: error getting filings – {e}")
        continue

    target = None
    for f in filings:
        if has_item(f, '2.02'):
            target = f
            break

    if target is None:
        print(f"{ticker}: no 8‑K with 2.02 found around {last_report_date}")
        continue

    try:
        filing_obj = target.obj()
        text = filing_obj.text()
    except Exception as e:
        print(f"{ticker}: could not get text – {e}")
        continue

    lower_text = text.lower()
    search_start = 0

    # Single-word indicators (unchanged)
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

    while True:
        idx = lower_text.find('guidance', search_start)
        if idx == -1:
            break

        start_idx = max(0, idx - 200)
        end_idx   = min(len(lower_text), idx + 500)
        snippet = lower_text[start_idx:end_idx]

        # Check for raise words with proximity & negation filter
        snippet_raise = False
        for word in raise_words:
            pos = snippet.find(word)
            if pos == -1:
                continue
            # Check proximity: word must be within 100 characters of 'guidance'
            snippet_guidance_pos = snippet.find('guidance')
            if abs(pos - snippet_guidance_pos) <= 100:
                # Check for negation immediately before the word
                before_word = snippet[max(0, pos-20):pos]
                if not any(neg in before_word for neg in ['not ', 'no ', 'may not ', 'without ']):
                    snippet_raise = True
                    break

        snippet_affirm = False
        for word in affirm_words:
            pos = snippet.find(word)
            if pos == -1:
                continue
            # Same proximity rule (optional for affirm, but helpful)
            snippet_guidance_pos = snippet.find('guidance')
            if abs(pos - snippet_guidance_pos) <= 100:
                before_word = snippet[max(0, pos-20):pos]
                if not any(neg in before_word for neg in ['not ', 'no ', 'may not ']):
                    snippet_affirm = True
                    break

        if snippet_raise:
            guidance_valid = 1
            print(f"\n=== {ticker} RAISE SNIPPET ===")
            print(snippet)
            break
        elif snippet_affirm:
            guidance_valid = 0
            print(f"\n=== {ticker} AFFIRM SNIPPET ===")
            print(snippet)
            break

        search_start = idx + 1

    print(f"{ticker}: guidance_valid = {guidance_valid}")

    c.execute("UPDATE features SET guidance_valid = ? WHERE ticker = ? AND earnings_date = ?",
              (guidance_valid, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()

conn.close()