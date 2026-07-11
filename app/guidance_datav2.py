# guidance_labeler_v9_final.py
import re
from datetime import timedelta
import pandas as pd
import edgar
import sqlite3
import json
import time

edgar.set_identity("sachiomaximilliano166@gmail.com")

def extract_guidance_rich(ticker, as_of_date, earnings_lookup):
    """
    Returns dict:
        label, confidence_score, confidence_level, classification_reason,
        guidance_items (list), best_per_type (dict),
        ticker, earnings_date, filing_date, accession
    label: 0=lower, 1=maintain, 2=raise, 3=no guidance
    """
    # ---------- constants ----------
    safe_stems = ['guidance', 'outlook', 'forecast']
    generic_stems = ['expect', 'anticipate', 'project']
    raise_words = ['raise','raises','raised','raising','increase','increases','increased','increasing',
                   'boost','boosts','boosted','boosting','upgrade','upgrades','upgraded','upgrading',
                   'upward','higher','stronger','improve','narrow']
    lower_words = ['lower','lowers','lowered','lowering','decrease','decreases','decreased','decreasing',
                   'reduce','reduces','reduced','reducing','cut','cuts','cutting','downward','weaker','worsen']
    maintain_words = ['reaffirm','reaffirms','reaffirmed','reaffirming','maintain','maintains','maintained',
                      'maintaining','unchanged','no change','consistent with prior']
    revision_signals = ['now','previously','prior','revised','updated']
    financial_metrics = [
        'revenue','sales','eps','earnings','ebitda','margin','fiscal','fy','quarter','growth',
        'operating income','net income','free cash flow','fcf','arr','bookings','comparable sales',
        'adjusted','outlook','forecast','guidance','operating profit','gaap eps','non-gaap eps',
        'adjusted eps','cash flow','organic growth','same store sales','subscription revenue',
        'annual recurring revenue','capex','book value','gross margin','operating margin',
        'diluted eps','organic revenue','constant currency','gross profit','segment revenue',
        'operating cash flow','loan growth','net interest income','subscribers','units'
    ]
    guidance_type_map = {
        'revenue': ['revenue','sales','organic revenue','subscription revenue','comparable sales',
                    'same store sales','segment revenue','loan growth'],
        'eps': ['eps','earnings','gaap eps','non-gaap eps','adjusted eps','diluted eps'],
        'ebitda': ['ebitda'],
        'margin': ['margin','gross margin','operating margin'],
        'cash_flow': ['cash flow','free cash flow','fcf','operating cash flow'],
        'arr_bookings': ['arr','bookings','annual recurring revenue'],
        'subscribers_units': ['subscribers','units','production','shipments'],
        'other': ['capex','book value','organic growth','constant currency','adjusted','operating profit',
                  'net income','net interest income']
    }
    negation_phrases = [
        'not ',"n't ",'no ','without ','unlikely ','failed ','less likely ',
        'cannot ','did not ','does not ','do not ','not expected ','never ',
        'no longer ','declined to ','reduced its','lower its'
    ]

    # ---------- helpers ----------
    def empty_result():
        return {
            'label': 3, 'confidence_score': 0, 'confidence_level': 'No guidance',
            'classification_reason': 'No guidance found', 'guidance_items': [],
            'best_per_type': {}, 'ticker': ticker, 'earnings_date': str(as_of_date),
            'filing_date': None, 'accession': None
        }

    def sentence_split(text):
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        sentences = []
        for para in paragraphs:
            parts = re.split(r'(?<!\d);(?!\d)', para)
            for part in parts:
                sents = re.split(r'(?<!\d)(?<!\b[A-Z])(?<!\b[A-Z][a-z])\.(?=\s+|\s*$)', part)
                final = []
                for s in sents:
                    final.extend(re.split(r'(?<=\?|!)(?=\s+)', s))
                sentences.extend([s.strip() for s in final if s.strip()])
        return sentences

    def has_negation(pre_text):
        pre_lower = pre_text.lower()
        return any(neg in pre_lower for neg in negation_phrases)

    def detect_guidance_type(sentence):
        for gtype, keywords in guidance_type_map.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', sentence):
                    return gtype
        return 'unknown'

    # ---- numerical parsing with units ----
    def normalize_number(tok, is_percent=False):
        if is_percent:
            clean = tok.replace('%', '').strip()
            try:
                return float(clean), 'percent'
            except ValueError:
                return None, None

        orig = tok.replace('$', '').strip()
        orig = orig.replace(',', '')
        multipliers = {
            'billion': 1e9, 'billions': 1e9, 'b': 1e9,
            'million': 1e6, 'millions': 1e6, 'm': 1e6,
            'thousand': 1e3, 'k': 1e3,
        }
        num_part = ''
        suffix = ''
        for i, ch in enumerate(orig):
            if ch.isdigit() or ch == '.':
                num_part += ch
            else:
                suffix = orig[i:].strip().lower()
                break
        if not num_part:
            return None, None
        try:
            val = float(num_part)
        except ValueError:
            return None, None
        if suffix in multipliers:
            val *= multipliers[suffix]
            return val, 'dollar'
        return val, 'dollar'

    def parse_range(tok, is_percent=False):
        tok = tok.strip()
        parts = re.split(r'\s*[-–]\s*', tok)
        if len(parts) != 2:
            return None, None, None
        low_val, low_unit = normalize_number(parts[0], is_percent)
        high_val, high_unit = normalize_number(parts[1], is_percent)
        if low_val is None or high_val is None:
            return None, None, None
        if low_unit != high_unit:
            return None, None, None
        return low_val, high_val, low_unit

    def detect_numerical_revision(text):
        """
        Look for pairs of numbers (ranges or singles) that represent old vs new guidance.
        Returns (label, evidence) or (None, None).
        """
        # Patterns for ranges and singles (unchanged)
        range_pat = r'(\$?\d+\.?\d*\s*[BMKbmk]?\s*[-–]\s*\$?\d+\.?\d*\s*[BMKbmk]?)'
        single_pat = r'(\$?\d+\.?\d*\s*[BMKbmk]?(?:\s*(?i:billion|million|thousand))?)'
        percent_single_pat = r'(\d+\.?\d*\s*%)'

        # Define which signals indicate old / new guidance
        OLD_SIGNALS = {'previously', 'prior', 'old', 'before', 'last'}
        NEW_SIGNALS = {'now', 'updated', 'new', 'current', 'revised', 'after'}

        # Split on all revision words
        parts = re.split(
            r'\b(?:previously|prior|old|before|last|now|updated|new|current|revised|after)\b',
            text, flags=re.IGNORECASE
        )

        # Find the actual matches to determine their order
        matches = list(re.finditer(
            r'\b(?:previously|prior|old|before|last|now|updated|new|current|revised|after)\b',
            text, flags=re.IGNORECASE
        ))

        # We need at least two revision signals and three text segments
        if len(matches) >= 2 and len(parts) >= 3:
            first_word = matches[-2].group().lower()
            second_word = matches[-1].group().lower()

            # Determine which segment is prior and which is current
            if first_word in OLD_SIGNALS and second_word in NEW_SIGNALS:
                # Old before New → parts[-2] is prior, parts[-1] is current
                prior_part = parts[-2]
                current_part = parts[-1]
            elif first_word in NEW_SIGNALS and second_word in OLD_SIGNALS:
                # New before Old → parts[-2] is actually current, parts[-1] is prior
                prior_part = parts[-1]
                current_part = parts[-2]
            else:
                # Two old or two new signals – unreliable
                prior_part, current_part = None, None

            if prior_part and current_part:
                is_percent = '%' in prior_part or '%' in current_part

                # Try ranges first
                prior_range = re.search(range_pat, prior_part)
                current_range = re.search(range_pat, current_part)
                if prior_range and current_range:
                    pl, ph, pu = parse_range(prior_range.group(1), is_percent)
                    cl, ch, cu = parse_range(current_range.group(1), is_percent)
                    if None not in (pl, ph, cl, ch) and pu == cu:
                        return compare_ranges(pl, ph, cl, ch, pu)

                # Singles (dollar or percent)
                if is_percent:
                    prior_single = re.search(percent_single_pat, prior_part)
                    current_single = re.search(percent_single_pat, current_part)
                    if prior_single and current_single:
                        pv = normalize_number(prior_single.group(1), is_percent=True)[0]
                        cv = normalize_number(current_single.group(1), is_percent=True)[0]
                        if pv is not None and cv is not None:
                            return compare_singles(pv, cv, 'percent')
                else:
                    prior_single = re.search(single_pat, prior_part)
                    current_single = re.search(single_pat, current_part)
                    if prior_single and current_single:
                        pv, pu = normalize_number(prior_single.group(1))
                        cv, cu = normalize_number(current_single.group(1))
                        if None not in (pv, cv) and pu == cu:
                            return compare_singles(pv, cv, pu)

        # Alternative: "from X to Y" pattern (unchanged)
        from_to_pat = r'(?:from|previously)\s+(' + single_pat + r')\s*(?:to|now)\s+(' + single_pat + r')'
        from_to = re.search(from_to_pat, text, re.IGNORECASE)
        if from_to:
            old_val, old_unit = normalize_number(from_to.group(1))
            new_val, new_unit = normalize_number(from_to.group(2))
            if None not in (old_val, new_val) and old_unit == new_unit:
                return compare_singles(old_val, new_val, old_unit)

        return None, None

    def compare_ranges(old_low, old_high, new_low, new_high, unit):
        def pct_change(old, new):
            return (new - old) / abs(old) if old != 0 else 0

        low_change = pct_change(old_low, new_low)
        high_change = pct_change(old_high, new_high)
        mid_old = (old_low + old_high) / 2
        mid_new = (new_low + new_high) / 2
        mid_change = pct_change(mid_old, mid_new)

        if mid_change > 0.02:
            label = 2
        elif mid_change < -0.02:
            label = 0
        else:
            if low_change > 0.02 and high_change > 0.02:
                label = 2
            elif low_change < -0.02 and high_change < -0.02:
                label = 0
            else:
                label = 1

        evidence = {
            'numerical_revision': True,
            'unit': unit,
            'old_range': [round(old_low, 4), round(old_high, 4)],
            'new_range': [round(new_low, 4), round(new_high, 4)],
            'low_change_pct': round(low_change * 100, 1),
            'high_change_pct': round(high_change * 100, 1),
            'mid_change_pct': round(mid_change * 100, 1),
            'range_widened': (new_high - new_low) > (old_high - old_low) * 1.02,
            'range_narrowed': (new_high - new_low) < (old_high - old_low) * 0.98
        }
        return label, evidence

    def compare_singles(old_val, new_val, unit):
        change = (new_val - old_val) / abs(old_val) if old_val != 0 else 0
        if change > 0.02:
            label = 2
        elif change < -0.02:
            label = 0
        else:
            label = 1
        evidence = {
            'numerical_revision': True,
            'unit': unit,
            'old_value': round(old_val, 4),
            'new_value': round(new_val, 4),
            'change_pct': round(change * 100, 1)
        }
        return label, evidence

    # ---------- classify sentence ----------
    def classify_sentence(sentences, stem):
        main_idx = None
        for i, s in enumerate(sentences):
            if stem in s:
                main_idx = i
                break
        if main_idx is None:
            return None
        main_sent = sentences[main_idx]
        gtype = detect_guidance_type(main_sent)

        para = ' '.join(sentences[max(0, main_idx-1): main_idx+2])
        num_label, num_ev = detect_numerical_revision(para)
        if num_label is not None:
            return (num_label, 'numerical_revision', num_ev, gtype)

        best_label = None
        best_word = None
        best_dist = 9999
        for word_list, label in [(raise_words, 2), (lower_words, 0), (maintain_words, 1)]:
            for w in word_list:
                for m in re.finditer(r'\b' + re.escape(w) + r'\b', main_sent):
                    start = m.start()
                    if not has_negation(main_sent[max(0, start-40):start]):
                        dist = abs(main_sent.find(stem) - start)
                        if dist < best_dist:
                            best_dist = dist
                            best_word = w
                            best_label = label
        if best_label is None:
            return None

        evidence = {
            'stem': stem,
            'action_word': best_word,
            'in_main_sentence': True,
            'metric_nearby': any(re.search(r'\b' + re.escape(m) + r'\b', main_sent) for m in financial_metrics),
            'revision_nearby': any(re.search(r'\b' + re.escape(rw) + r'\b', main_sent) for rw in revision_signals),
            'numerical_revision': False,
            'distance_chars': best_dist
        }
        return (best_label, best_word, evidence, gtype)

    def compute_confidence(evidence):
        if isinstance(evidence, dict) and evidence.get('numerical_revision'):
            return 95
        score = 0
        if evidence.get('action_word'): score += 50
        if evidence.get('metric_nearby'): score += 20
        if evidence.get('revision_nearby'): score += 20
        if evidence.get('in_main_sentence'): score += 10
        return score

    def reason(item):
        ev = item['evidence']
        if isinstance(ev, dict) and ev.get('numerical_revision'):
            return 'Numerical revision detected'
        parts = []
        if ev.get('action_word'): parts.append(f"Keyword '{item['trigger_word']}' found")
        if ev.get('revision_nearby'): parts.append('Revision signal nearby')
        if ev.get('metric_nearby'): parts.append('Financial metric in sentence')
        return ', '.join(parts) if parts else 'Weak signal'

    # ---------- filing search ----------
    ed_series = earnings_lookup.get(ticker, pd.Series(dtype='datetime64[ns]'))
    past = ed_series[ed_series < pd.Timestamp(as_of_date)]
    if past.empty:
        print(f"[ERROR] {ticker}: no past data")
        return empty_result()

    prior_date = past.sort_values(ascending=False).iloc[0].date()
    start = prior_date - timedelta(days=2)
    end   = prior_date + timedelta(days=2)

    try:
        company = edgar.Company(ticker)
        filings = company.get_filings(form="8-K",
                                      filing_date=f"{start}:{end}")
    except Exception as e:
        print(f"[ERROR] {ticker}: {e}")
        return empty_result()

    # ---------- helper to process a single text block ----------
    def process_text(txt, src):
        """Return list of guidance items found in a single text block (body or exhibit)."""
        items = []
        paragraphs = [p.strip() for p in txt.split('\n\n') if p.strip()]
        if not paragraphs:
            paragraphs = [txt]
        for para in paragraphs:
            for stem in safe_stems + generic_stems:
                if stem not in para:
                    continue
                if stem in generic_stems:
                    if not (any(re.search(r'\b' + re.escape(m) + r'\b', para) for m in financial_metrics) and
                            any(re.search(r'\b' + re.escape(rw) + r'\b', para) for rw in revision_signals)):
                        continue
                sents = sentence_split(para)
                if not sents:
                    continue
                res = classify_sentence(sents, stem)
                if res:
                    label, trigger, ev, gtype = res
                    main_sent = next((s for s in sents if stem in s), '')
                    item = {
                        'label': label,
                        'stem': stem,
                        'trigger_word': trigger,
                        'guidance_type': gtype,
                        'matched_sentence': main_sent,
                        'paragraph': para,
                        'snippet': main_sent[:600] if main_sent else para[:600],
                        'evidence': ev,
                        'source': src,
                        'confidence_score': compute_confidence(ev)
                    }
                    items.append(item)
        return items

    # ---------- iterate filings ----------
    best_items = []
    best_score = -1
    filing_date = None
    accession = None

    for f in filings:
        try:
            acc = f.accession_number if hasattr(f, 'accession_number') else None
            fd = f.filing_date
            if hasattr(fd, 'strftime'):
                fd = fd.strftime('%Y-%m-%d')
        except:
            continue

        body = ''
        exhibits = []
        try:
            body = f.obj().text()
        except Exception as e:
            print(f"  [WARN] Could not get body text for {ticker}: {e}")
        try:
            for att in f.attachments:
                # Use document_type, fallback to description if document_type is empty
                doc_id = getattr(att, 'document_type', '') or getattr(att, 'description', '')
                if 'EX-99.' in doc_id:
                    try:
                        exhibits.append(att.text())
                    except Exception as e:
                        print(f"  [WARN] Could not extract exhibit {doc_id}: {e}")
        except Exception as e:
            print(f"  [WARN] Error iterating attachments for {ticker}: {e}")

        filing_items = []
        if isinstance(body, str):
            filing_items.extend(process_text(body.lower(), "body"))

        for et in exhibits:
            if isinstance(et, str):
                filing_items.extend(process_text(et.lower(), "exhibit"))

        if not filing_items:
            continue

        best_item = max(filing_items, key=lambda x: x['confidence_score'])
        if best_item['confidence_score'] > best_score:
            best_score = best_item['confidence_score']
            best_items = filing_items
            filing_date = fd
            accession = acc

    if not best_items:
        print(f"error - {ticker} {ed}: no best items")
        return empty_result()

    best_per_type = {}
    for item in best_items:
        gt = item['guidance_type']
        if gt not in best_per_type or item['confidence_score'] > best_per_type[gt]['confidence_score']:
            best_per_type[gt] = item

    overall = max(best_items, key=lambda x: x['confidence_score'])
    score = overall['confidence_score']
    level = 'Very High' if score >= 90 else 'High' if score >= 70 else 'Medium' if score >= 30 else 'Low'

    return {
        'label': overall['label'],
        'confidence_score': score,
        'confidence_level': level,
        'classification_reason': reason(overall),
        'guidance_items': best_items,
        'best_per_type': best_per_type,
        'ticker': ticker,
        'earnings_date': str(as_of_date),
        'filing_date': filing_date,
        'accession': accession
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
DB_PATH = 'data/universe.db'
BATCH_SIZE = 500
COMMIT_EVERY = 100

conn = sqlite3.connect(
    DB_PATH,
    timeout=30,
    check_same_thread=False
)

conn.execute("PRAGMA journal_mode=WAL;")
conn.execute("PRAGMA synchronous=NORMAL;")

c = conn.cursor()

c.execute("""
    CREATE TABLE IF NOT EXISTS guidance_datasetv2 (
        ticker              TEXT,
        earnings_date       TEXT,
        label               INTEGER,
        confidence_score    INTEGER,
        confidence_level    TEXT,
        classification_reason TEXT,
        guidance_items      TEXT,
        best_per_type       TEXT,
        matched_sentence    TEXT,
        paragraph           TEXT,
        guidance_type       TEXT,
        source              TEXT,
        filing_date         TEXT,
        accession           TEXT,
        numerical_revision_evidence TEXT,
        raw_section         TEXT,
        PRIMARY KEY (ticker, earnings_date)
    )
""")
conn.commit()

# ---------------------------------------------------------------------------
# Load earnings history ONCE – no per-ticker DB connections
# ---------------------------------------------------------------------------
print("Loading earnings history into memory...")
all_earnings = pd.read_sql(
    "SELECT ticker, earnings_date FROM earnings_history ORDER BY ticker, earnings_date",
    conn,
    parse_dates=['earnings_date']
)
earnings_lookup = {}
for ticker, group in all_earnings.groupby('ticker'):
    earnings_lookup[ticker] = group['earnings_date'].sort_values().reset_index(drop=True)
print(f"Loaded earnings history for {len(earnings_lookup)} tickers.")

# ---------------------------------------------------------------------------
# Select rows that need processing (resumable LEFT JOIN)
# ---------------------------------------------------------------------------
df_todo = pd.read_sql("""
    SELECT m.ticker, m.earnings_date
    FROM ml_dataset m
    LEFT JOIN guidance_datasetv2 g
        ON m.ticker = g.ticker
        AND m.earnings_date = g.earnings_date
    WHERE g.ticker IS NULL
      AND m.target_5d_drift IS NOT NULL
      AND m.earnings_date < date('now')
    ORDER BY m.earnings_date ASC
    LIMIT ?
""", conn, params=(BATCH_SIZE,), parse_dates=['earnings_date'])

if df_todo.empty:
    print("No new rows to process. All caught up!")
    conn.close()
    exit()

print(f"Processing {len(df_todo)} rows...")

rows_processed = 0

for idx, row in df_todo.iterrows():
    ticker = row['ticker']
    ed = row['earnings_date'].date()

    try:
        res = extract_guidance_rich(ticker, ed, earnings_lookup)
    except Exception as e:
        print(f"  ERROR on {ticker} {ed}: {e}")
        res = {
            'label': 3,
            'confidence_score': 0,
            'confidence_level': 'No guidance',
            'classification_reason': f'Extraction error: {e}',
            'guidance_items': [],
            'best_per_type': {},
            'filing_date': None,
            'accession': None
        }

    if res['guidance_items']:
        res['guidance_items'] = sorted(
            res['guidance_items'],
            key=lambda x: x['confidence_score'],
            reverse=True
        )

    best = res['guidance_items'][0] if res['guidance_items'] else None

    guidance_items_json = json.dumps(res['guidance_items']) if res['guidance_items'] else None
    best_per_type_json = json.dumps(res['best_per_type']) if res['best_per_type'] else None
    num_ev_json = (
        json.dumps(best['evidence'])
        if best and best['evidence'].get('numerical_revision')
        else None
    )

    c.execute("""
        INSERT OR REPLACE INTO guidance_datasetv2 (
            ticker, earnings_date, label, confidence_score, confidence_level,
            classification_reason, guidance_items, best_per_type,
            matched_sentence, paragraph, guidance_type, source,
            filing_date, accession, numerical_revision_evidence, raw_section
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticker,
        ed.strftime('%Y-%m-%d'),
        res['label'],
        res['confidence_score'],
        res['confidence_level'],
        res['classification_reason'],
        guidance_items_json,
        best_per_type_json,
        best['matched_sentence'] if best else None,
        best['paragraph'] if best else None,
        best['guidance_type'] if best else None,
        best.get('source') if best else None,
        res['filing_date'],
        res['accession'],
        num_ev_json,
        None
    ))
    if (rows_processed + 1) % COMMIT_EVERY == 0:
        conn.commit()
        print(f"  Committed {rows_processed+1} rows...")

    rows_processed += 1
    time.sleep(0.15)

conn.commit()
conn.close()
print(f"Batch complete. {rows_processed} rows inserted/updated.")