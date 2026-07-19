# extract_guidance_llm_v21_final.py
import sqlite3
import pandas as pd
import json
import re
import hashlib
import time
import traceback
import logging
from datetime import datetime, timedelta
from groq import Groq, APIConnectionError, RateLimitError, APIStatusError
from config import GROQ_API_KEY

client = Groq(api_key=GROQ_API_KEY)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_PATH = "C:/Users/Sachio/Desktop/earnings-catalyst-screener/data/universe.db"
PROMPT_VERSION = "v2"
PARSER_VERSION = "v3"
MODEL_NAME = "llama-3.3-70b-versatile"
TEMPERATURE = 0.0
TOP_P = 1.0
MAX_TOKENS = 500
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0
BATCH_SIZE = 500
COMMIT_EVERY = 500
INPUT_PRICE_PER_1M = 0.59
OUTPUT_PRICE_PER_1M = 0.79
STALE_PROCESSING_MINUTES = 30

STATUS_PENDING = 'pending'
STATUS_PROCESSING = 'processing'
STATUS_DONE = 'done'
STATUS_FAILED = 'failed'
STATUS_CACHED = 'cached'

GUIDANCE_PROMPT_TEMPLATE = """Extract guidance from 8-K text.
Key: "{matched_sentence}"
Context: "{paragraph}"

Return JSON:
{{"guidance_present":bool,"eps":{{"label":"raise"/"lower"/"maintain"/"first_time"/"none","current_range":[low,high]|null,"previous_range":[low,high]|null,"previous_growth_pct":num|null,"current_growth_pct":num|null}},"revenue":{{"label":"raise"/"lower"/"maintain"/"first_time"/"none","current_range":[low,high]|null,"previous_range":[low,high]|null,"previous_growth_pct":num|null,"current_growth_pct":num|null}},"evidence":["exact quotes"],"has_numeric_guidance":bool,"has_range":bool,"has_percent":bool,"evidence_count":int}}

Labels: raise=outlook up, lower=outlook down, maintain=reaffirmed, first_time=initial.
Extract growth rates only if explicitly stated. Return ONLY JSON."""

RISK_TONE_PROMPT_TEMPLATE = """Extract risks and tone from 8-K text.
Key: "{matched_sentence}"
Context: "{paragraph}"

Return JSON:
{{"risks":{{"risks_present":bool,"risks":[{{"category":"tariffs"/"demand"/"inflation"/"supply_chain"/"competition"/"regulation"/"macro"/"other","description":"...","severity":"high"/"medium"/"low","evidence":"..."}}],"risk_count":int,"overall_risk_level":"high"/"medium"/"low"/"none"}},"tone":{{"tone_present":bool,"certainty":"high"/"medium"/"low","sentiment":"positive"/"neutral"/"cautious"/"negative","language_markers":["..."],"evidence":"..."}}}}

Tone: high=definitive(will,expect,confident), medium=moderate(believe,anticipate), low=hedging(may,could,depending).
Return ONLY JSON."""

GUIDANCE_PROMPT_HASH = hashlib.sha256((GUIDANCE_PROMPT_TEMPLATE + PROMPT_VERSION).encode()).hexdigest()[:12]
RISK_TONE_PROMPT_HASH = hashlib.sha256((RISK_TONE_PROMPT_TEMPLATE + PROMPT_VERSION).encode()).hexdigest()[:12]

VALID_LABELS = {"raise", "lower", "maintain", "first_time", "none"}
VALID_SEVERITY = {"high", "medium", "low"}
VALID_RISK_LEVEL = {"high", "medium", "low", "none"}
VALID_CERTAINTY = {"high", "medium", "low"}
VALID_SENTIMENT = {"positive", "neutral", "cautious", "negative"}
VALID_RISK_CATEGORIES = {"tariffs", "demand", "inflation", "supply_chain", "competition", "regulation", "macro", "other"}


# ---------------------------------------------------------------------------
# Table creation
# ---------------------------------------------------------------------------
def create_all_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS guidance_llm (
            ticker TEXT, earnings_date TEXT,
            guidance_present INTEGER,
            eps_label TEXT, eps_current_range TEXT, eps_previous_range TEXT,
            eps_previous_growth REAL, eps_current_growth REAL,
            revenue_label TEXT, revenue_current_range TEXT, revenue_previous_range TEXT,
            revenue_previous_growth REAL, revenue_current_growth REAL,
            growth_deceleration_eps REAL, growth_deceleration_revenue REAL,
            evidence TEXT, evidence_count INTEGER,
            has_numeric_guidance INTEGER, has_range INTEGER, has_percent INTEGER,
            document_hash TEXT, prompt_hash TEXT, prompt_version TEXT,
            parser_version TEXT, model_name TEXT,
            temperature REAL, top_p REAL, max_tokens INTEGER,
            raw_response TEXT, normalized_json TEXT, raw_response_hash TEXT,
            validation_status TEXT,
            guidance_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, earnings_date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS risks_llm (
            ticker TEXT, earnings_date TEXT,
            risks_present INTEGER, risk_count INTEGER, overall_risk_level TEXT,
            risks_json TEXT,
            document_hash TEXT, prompt_hash TEXT, prompt_version TEXT,
            parser_version TEXT, model_name TEXT,
            temperature REAL, top_p REAL, max_tokens INTEGER,
            raw_response TEXT, normalized_json TEXT, raw_response_hash TEXT,
            risks_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, earnings_date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tone_llm (
            ticker TEXT, earnings_date TEXT,
            tone_present INTEGER, certainty TEXT, sentiment TEXT,
            language_markers TEXT, evidence TEXT,
            document_hash TEXT, prompt_hash TEXT, prompt_version TEXT,
            parser_version TEXT, model_name TEXT,
            temperature REAL, top_p REAL, max_tokens INTEGER,
            raw_response TEXT, normalized_json TEXT, raw_response_hash TEXT,
            tone_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, earnings_date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS llm_usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT, earnings_date TEXT, extractor TEXT,
            model_name TEXT, prompt_hash TEXT, prompt_version TEXT, parser_version TEXT,
            temperature REAL, top_p REAL, max_tokens INTEGER,
            prompt_tokens INTEGER, completion_tokens INTEGER, total_tokens INTEGER,
            input_chars INTEGER, output_chars INTEGER,
            latency_ms REAL, processing_time_seconds REAL, cost_estimate REAL,
            input_price REAL, output_price REAL,
            retries_used INTEGER DEFAULT 0, cached INTEGER DEFAULT 0,
            response_id TEXT, finish_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS failed_llm (
            ticker TEXT, earnings_date TEXT, extractor TEXT,
            model_name TEXT, prompt_hash TEXT, document_hash TEXT,
            error_message TEXT, error_traceback TEXT,
            attempts INTEGER DEFAULT 1,
            last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (ticker, earnings_date, extractor)
        )
    """)

    for table in ['guidance_llm', 'risks_llm', 'tone_llm']:
        for col, col_type in [('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                              ('raw_response_hash', 'TEXT'), ('normalized_json', 'TEXT')]:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass
    for col, col_type in [('input_price', 'REAL DEFAULT 0.59'), ('output_price', 'REAL DEFAULT 0.79'),
                          ('response_id', 'TEXT'), ('finish_reason', 'TEXT')]:
        try:
            conn.execute(f"ALTER TABLE llm_usage_log ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass
    for col, col_type in [('model_name', 'TEXT'), ('prompt_hash', 'TEXT'), ('document_hash', 'TEXT')]:
        try:
            conn.execute(f"ALTER TABLE failed_llm ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass

    conn.execute("CREATE INDEX IF NOT EXISTS idx_guidance_llm_status ON guidance_llm(guidance_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_guidance_llm_hash ON guidance_llm(document_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_guidance_llm_updated ON guidance_llm(updated_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_risks_llm_hash ON risks_llm(document_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_risks_llm_updated ON risks_llm(updated_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tone_llm_hash ON tone_llm(document_hash)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tone_llm_updated ON tone_llm(updated_at)")
    conn.commit()
    logger.info("All LLM tables, indexes, and migrations verified.")


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------
def _to_json(obj):
    return json.dumps(obj, ensure_ascii=False)


def _from_json(text):
    if text is None:
        return None
    return json.loads(text)


def _json_nullable(obj):
    return None if obj is None else _to_json(obj)


def _get_section(obj, key):
    return (obj or {}).get(key) or {}


def _compute_midpoint(r):
    if r and len(r) == 2 and r[0] is not None and r[1] is not None:
        return (r[0] + r[1]) / 2
    return None


# ---------------------------------------------------------------------------
# Schema validation – strengthened
# ---------------------------------------------------------------------------
def _is_valid_number(x):
    return x is None or isinstance(x, (int, float))


def validate_guidance_parsed(parsed, paragraph=''):
    if not isinstance(parsed, dict):
        return False
    for metric in ['eps', 'revenue']:
        m = _get_section(parsed, metric)
        label = m.get('label', 'none')
        if label not in VALID_LABELS:
            return False
        for rkey in ['current_range', 'previous_range']:
            r = m.get(rkey)
            if r is not None:
                if not isinstance(r, list) or len(r) != 2:
                    return False
                if not all(_is_valid_number(v) for v in r):
                    return False
                if r[0] is not None and r[1] is not None and r[0] > r[1]:
                    return False
        for gkey in ['previous_growth_pct', 'current_growth_pct']:
            val = m.get(gkey)
            if not _is_valid_number(val):
                return False
            if val is not None and (val < -100 or val > 500):
                return False
        cur = _compute_midpoint(m.get('current_range'))
        prev = _compute_midpoint(m.get('previous_range'))
        if cur is not None and prev is not None and prev != 0:
            pct = (cur - prev) / abs(prev)
            if label == 'raise' and pct <= 0.01:
                return False
            if label == 'lower' and pct >= -0.01:
                return False
            if label == 'maintain' and abs(pct) > 0.02:
                return False
        if label in ('raise', 'lower', 'first_time'):
            has_range = m.get('current_range') is not None
            has_growth = m.get('current_growth_pct') is not None
            has_evidence = bool(parsed.get('evidence'))
            if not (has_range or has_growth or has_evidence):
                return False
            ev = parsed.get('evidence')
            if ev is not None and len(ev) == 0:
                return False
    ev = parsed.get('evidence')
    if ev is not None:
        if not isinstance(ev, list):
            return False
        expected_count = parsed.get('evidence_count', 0)
        if len(ev) != expected_count:
            return False
        if paragraph:
            for q in ev:
                if q and q not in paragraph:
                    return False
    if parsed.get('guidance_present') and (not ev or len(ev) == 0):
        return False
    return True


def validate_risks_tone_parsed(parsed):
    if not isinstance(parsed, dict):
        return False
    risks = _get_section(parsed, 'risks')
    if risks.get('overall_risk_level', 'none') not in VALID_RISK_LEVEL:
        return False
    if risks.get('risk_count', 0) != len(risks.get('risks', [])):
        return False
    for r in risks.get('risks', []):
        if r.get('category') not in VALID_RISK_CATEGORIES:
            return False
        if r.get('severity') not in VALID_SEVERITY:
            return False
        if not r.get('description') or not r.get('evidence'):
            return False
    tone = _get_section(parsed, 'tone')
    if tone.get('certainty', 'unknown') not in VALID_CERTAINTY:
        return False
    if tone.get('sentiment', 'unknown') not in VALID_SENTIMENT:
        return False
    return True


# ---------------------------------------------------------------------------
# JSON parser
# ---------------------------------------------------------------------------
def parse_llm_json(raw):
    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(r'\{.*\}', raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    start = raw.find('{')
    end = raw.rfind('}')
    if start != -1 and end != -1 and start < end:
        try:
            return json.loads(raw[start:end+1])
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError:
        pass
    raise ValueError("No valid JSON object found")


# ---------------------------------------------------------------------------
# Shared LLM caller
# ---------------------------------------------------------------------------
def _call_llm(prompt, validator_fn, paragraph=''):
    last_error = None
    last_tb = None
    retries_used = 0

    for attempt in range(1, MAX_RETRIES + 1):
        retries_used = attempt
        start_time = time.perf_counter()
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=TEMPERATURE,
                top_p=TOP_P,
                max_tokens=MAX_TOKENS,
            )
            latency_ms = (time.perf_counter() - start_time) * 1000
            raw = response.choices[0].message.content.strip()

            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0
            cost = (prompt_tokens / 1_000_000) * INPUT_PRICE_PER_1M + (completion_tokens / 1_000_000) * OUTPUT_PRICE_PER_1M
            input_chars = len(prompt)
            output_chars = len(raw)
            response_id = response.id if hasattr(response, 'id') else None
            finish_reason = response.choices[0].finish_reason if response.choices and hasattr(response.choices[0], 'finish_reason') else None

            parsed = parse_llm_json(raw)
            if not validator_fn(parsed, paragraph):
                raise ValueError("Schema validation failed, will retry")
            return parsed, raw, {
                'prompt_tokens': prompt_tokens, 'completion_tokens': completion_tokens,
                'total_tokens': total_tokens, 'latency_ms': latency_ms, 'cost': cost,
                'input_chars': input_chars, 'output_chars': output_chars,
                'retries_used': retries_used, 'cached': 0,
                'response_id': response_id, 'finish_reason': finish_reason,
            }, None, None
        except (APIConnectionError, RateLimitError, TimeoutError) as e:
            last_error = e
            last_tb = traceback.format_exc()
            logger.warning(f"  {type(e).__name__} attempt {attempt}/{MAX_RETRIES}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
        except APIStatusError as e:
            last_error = e
            last_tb = traceback.format_exc()
            logger.warning(f"  API status error (HTTP {e.status_code}) attempt {attempt}/{MAX_RETRIES}: {e}")
            if e.status_code >= 500 and attempt < MAX_RETRIES:
                time.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
            else:
                break
        except Exception as e:
            last_error = e
            last_tb = traceback.format_exc()
            logger.warning(f"  LLM attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BASE_DELAY * (2 ** (attempt - 1)))
    return None, None, None, last_error, last_tb


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------
def extract_guidance_llm(paragraph, matched_sentence):
    prompt = GUIDANCE_PROMPT_TEMPLATE.format(matched_sentence=matched_sentence, paragraph=paragraph)
    return _call_llm(prompt, validate_guidance_parsed, paragraph)


def extract_risks_tone_llm(paragraph, matched_sentence):
    prompt = RISK_TONE_PROMPT_TEMPLATE.format(matched_sentence=matched_sentence, paragraph=paragraph)
    return _call_llm(prompt, validate_risks_tone_parsed, '')


# ---------------------------------------------------------------------------
# Deterministic growth deceleration
# ---------------------------------------------------------------------------
def compute_growth_deceleration(prev_growth, curr_growth):
    if prev_growth is not None and curr_growth is not None:
        return round(prev_growth - curr_growth, 2)
    return None


# ---------------------------------------------------------------------------
# Validation status
# ---------------------------------------------------------------------------
def compute_validation_status(rule_label, eps_label, revenue_label):
    label_map = {'raise': 2, 'lower': 0, 'maintain': 1, 'first_time': 2, 'none': -1}
    llm_labels = []
    for llm_lbl in [eps_label, revenue_label]:
        mapped = label_map.get(llm_lbl, -1)
        if mapped != -1:
            llm_labels.append(mapped)
    if not llm_labels:
        return 'llm_no_guidance'
    if rule_label in llm_labels:
        if len(llm_labels) == 2 and all(l == rule_label for l in llm_labels):
            return 'agree'
        elif rule_label in llm_labels:
            return 'partial'
    if rule_label in (0, 1, 2) and all(l == -1 for l in [label_map.get(eps_label, -1), label_map.get(revenue_label, -1)]):
        return 'uncertain'
    opposite = {2: 0, 0: 2}
    if rule_label in opposite and opposite[rule_label] in llm_labels:
        return 'conflict'
    # EPS and Revenue give opposite signals
    if 0 in llm_labels and 2 in llm_labels:
        return 'mixed_signal'
    return 'disagree'


# ---------------------------------------------------------------------------
# Normalize text
# ---------------------------------------------------------------------------
def _normalize_text(txt):
    return re.sub(r'\s+', ' ', (txt or '').strip())


# ---------------------------------------------------------------------------
# Content hashing
# ---------------------------------------------------------------------------
def compute_content_hash(paragraph, matched_sentence, extractor_type):
    combined = _to_json([extractor_type, _normalize_text(paragraph), _normalize_text(matched_sentence)])
    return hashlib.sha256(combined.encode()).hexdigest()


def _compute_raw_hash(raw):
    return hashlib.sha256((raw or '').encode()).hexdigest()


# ---------------------------------------------------------------------------
# Cache lookup – verifies all generation parameters
# ---------------------------------------------------------------------------
def _cache_matches(d):
    return (d.get('prompt_hash') == GUIDANCE_PROMPT_HASH and
            d.get('model_name') == MODEL_NAME and
            d.get('parser_version') == PARSER_VERSION and
            d.get('temperature') == TEMPERATURE and
            d.get('top_p') == TOP_P and
            d.get('max_tokens') == MAX_TOKENS)


def lookup_cached_guidance(conn, content_hash):
    row = conn.execute("""
        SELECT guidance_present, eps_label, eps_current_range, eps_previous_range,
               eps_previous_growth, eps_current_growth,
               revenue_label, revenue_current_range, revenue_previous_range,
               revenue_previous_growth, revenue_current_growth,
               evidence, evidence_count, has_numeric_guidance, has_range, has_percent,
               raw_response, prompt_hash, model_name, parser_version,
               temperature, top_p, max_tokens
        FROM guidance_llm
        WHERE document_hash = ? AND guidance_status IN (?, ?)
        LIMIT 1
    """, (content_hash, STATUS_DONE, STATUS_CACHED)).fetchone()
    if row is None:
        return None
    d = dict(row)
    if not _cache_matches(d):
        return None
    parsed = {
        'guidance_present': bool(d.get('guidance_present', False)),
        'eps': {
            'label': d.get('eps_label'),
            'current_range': _from_json(d.get('eps_current_range')),
            'previous_range': _from_json(d.get('eps_previous_range')),
            'previous_growth_pct': d.get('eps_previous_growth'),
            'current_growth_pct': d.get('eps_current_growth'),
        },
        'revenue': {
            'label': d.get('revenue_label'),
            'current_range': _from_json(d.get('revenue_current_range')),
            'previous_range': _from_json(d.get('revenue_previous_range')),
            'previous_growth_pct': d.get('revenue_previous_growth'),
            'current_growth_pct': d.get('revenue_current_growth'),
        },
        'evidence': _from_json(d.get('evidence', '[]')),
        'evidence_count': d.get('evidence_count', 0),
        'has_numeric_guidance': bool(d.get('has_numeric_guidance', False)),
        'has_range': bool(d.get('has_range', False)),
        'has_percent': bool(d.get('has_percent', False)),
    }
    if not validate_guidance_parsed(parsed):
        return None
    return parsed, d.get('raw_response'), {'cached': 1}


def lookup_cached_risks_tone(conn, content_hash):
    row = conn.execute("""
        SELECT r.risks_present, r.risk_count, r.overall_risk_level, r.risks_json,
               t.tone_present, t.certainty, t.sentiment, t.language_markers, t.evidence,
               r.prompt_hash AS r_prompt_hash, r.model_name AS r_model_name, r.parser_version AS r_parser_version,
               r.temperature AS r_temperature, r.top_p AS r_top_p, r.max_tokens AS r_max_tokens,
               t.prompt_hash AS t_prompt_hash, t.model_name AS t_model_name, t.parser_version AS t_parser_version,
               t.temperature AS t_temperature, t.top_p AS t_top_p, t.max_tokens AS t_max_tokens
        FROM risks_llm r
        JOIN tone_llm t USING (ticker, earnings_date)
        WHERE r.document_hash = ? AND r.risks_status IN (?, ?)
          AND t.document_hash = ? AND t.tone_status IN (?, ?)
        LIMIT 1
    """, (content_hash, STATUS_DONE, STATUS_CACHED, content_hash, STATUS_DONE, STATUS_CACHED)).fetchone()
    if row is None:
        return None
    d = dict(row)
    if (d.get('r_prompt_hash') != RISK_TONE_PROMPT_HASH or d.get('r_model_name') != MODEL_NAME or d.get('r_parser_version') != PARSER_VERSION or
        d.get('r_temperature') != TEMPERATURE or d.get('r_top_p') != TOP_P or d.get('r_max_tokens') != MAX_TOKENS or
        d.get('t_prompt_hash') != RISK_TONE_PROMPT_HASH or d.get('t_model_name') != MODEL_NAME or d.get('t_parser_version') != PARSER_VERSION or
        d.get('t_temperature') != TEMPERATURE or d.get('t_top_p') != TOP_P or d.get('t_max_tokens') != MAX_TOKENS):
        return None
    parsed = {
        'risks': {
            'risks_present': bool(d.get('risks_present', False)),
            'risk_count': d.get('risk_count', 0),
            'overall_risk_level': d.get('overall_risk_level', 'none'),
            'risks': _from_json(d.get('risks_json', '[]')),
        },
        'tone': {
            'tone_present': bool(d.get('tone_present', False)),
            'certainty': d.get('certainty', 'unknown'),
            'sentiment': d.get('sentiment', 'unknown'),
            'language_markers': _from_json(d.get('language_markers', '[]')),
            'evidence': d.get('evidence', ''),
        }
    }
    if not validate_risks_tone_parsed(parsed):
        return None
    return parsed, None, {'cached': 1}


# ---------------------------------------------------------------------------
# Store results
# ---------------------------------------------------------------------------
def store_all_results(conn, ticker, ed, rule_label,
                      g_parsed, g_raw, g_usage,
                      rt_parsed, rt_raw, rt_usage,
                      content_hash, row_start_time):
    if g_parsed is None and rt_parsed is None:
        return
    elapsed = round(time.perf_counter() - row_start_time, 2)
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    if g_parsed:
        g = g_parsed
        eps = _get_section(g, 'eps')
        rev = _get_section(g, 'revenue')
        eps_decel = compute_growth_deceleration(eps.get('previous_growth_pct'), eps.get('current_growth_pct'))
        rev_decel = compute_growth_deceleration(rev.get('previous_growth_pct'), rev.get('current_growth_pct'))
        validation_status = compute_validation_status(rule_label, eps.get('label'), rev.get('label'))
        raw_hash = _compute_raw_hash(g_raw) if g_raw else None
        g_status = STATUS_CACHED if g_usage and g_usage.get('cached') else STATUS_DONE
        normalized_json = _to_json(g) if g else None

        conn.execute("""
            INSERT INTO guidance_llm (
                ticker, earnings_date, guidance_present,
                eps_label, eps_current_range, eps_previous_range,
                eps_previous_growth, eps_current_growth,
                revenue_label, revenue_current_range, revenue_previous_range,
                revenue_previous_growth, revenue_current_growth,
                growth_deceleration_eps, growth_deceleration_revenue,
                evidence, evidence_count,
                has_numeric_guidance, has_range, has_percent,
                document_hash, prompt_hash, prompt_version,
                parser_version, model_name,
                temperature, top_p, max_tokens,
                raw_response, normalized_json, raw_response_hash, validation_status,
                guidance_status, updated_at
            ) VALUES (
                :ticker, :ed, :gp,
                :eps_label, :eps_cur, :eps_prev,
                :eps_prev_growth, :eps_cur_growth,
                :rev_label, :rev_cur, :rev_prev,
                :rev_prev_growth, :rev_cur_growth,
                :eps_decel, :rev_decel,
                :evidence, :evidence_count,
                :has_num, :has_range, :has_pct,
                :doc_hash, :prompt_hash, :prompt_ver,
                :parser_ver, :model,
                :temp, :top_p, :max_tok,
                :raw, :norm_json, :raw_hash, :val_status,
                :guidance_status, :upd
            )
            ON CONFLICT (ticker, earnings_date) DO UPDATE SET
                guidance_present = excluded.guidance_present,
                eps_label = excluded.eps_label,
                eps_current_range = excluded.eps_current_range,
                eps_previous_range = excluded.eps_previous_range,
                eps_previous_growth = excluded.eps_previous_growth,
                eps_current_growth = excluded.eps_current_growth,
                revenue_label = excluded.revenue_label,
                revenue_current_range = excluded.revenue_current_range,
                revenue_previous_range = excluded.revenue_previous_range,
                revenue_previous_growth = excluded.revenue_previous_growth,
                revenue_current_growth = excluded.revenue_current_growth,
                growth_deceleration_eps = excluded.growth_deceleration_eps,
                growth_deceleration_revenue = excluded.growth_deceleration_revenue,
                evidence = excluded.evidence,
                evidence_count = excluded.evidence_count,
                has_numeric_guidance = excluded.has_numeric_guidance,
                has_range = excluded.has_range,
                has_percent = excluded.has_percent,
                document_hash = excluded.document_hash,
                prompt_hash = excluded.prompt_hash,
                prompt_version = excluded.prompt_version,
                parser_version = excluded.parser_version,
                model_name = excluded.model_name,
                temperature = excluded.temperature,
                top_p = excluded.top_p,
                max_tokens = excluded.max_tokens,
                raw_response = excluded.raw_response,
                normalized_json = excluded.normalized_json,
                raw_response_hash = excluded.raw_response_hash,
                validation_status = excluded.validation_status,
                guidance_status = excluded.guidance_status,
                updated_at = excluded.updated_at
        """, {
            'ticker': ticker, 'ed': ed,
            'gp': 1 if g.get('guidance_present') else 0,
            'eps_label': eps.get('label'),
            'eps_cur': _json_nullable(eps.get('current_range')),
            'eps_prev': _json_nullable(eps.get('previous_range')),
            'eps_prev_growth': eps.get('previous_growth_pct'),
            'eps_cur_growth': eps.get('current_growth_pct'),
            'rev_label': rev.get('label'),
            'rev_cur': _json_nullable(rev.get('current_range')),
            'rev_prev': _json_nullable(rev.get('previous_range')),
            'rev_prev_growth': rev.get('previous_growth_pct'),
            'rev_cur_growth': rev.get('current_growth_pct'),
            'eps_decel': eps_decel,
            'rev_decel': rev_decel,
            'evidence': _to_json(g.get('evidence', [])),
            'evidence_count': g.get('evidence_count', 0),
            'has_num': 1 if g.get('has_numeric_guidance') else 0,
            'has_range': 1 if g.get('has_range') else 0,
            'has_pct': 1 if g.get('has_percent') else 0,
            'doc_hash': content_hash,
            'prompt_hash': GUIDANCE_PROMPT_HASH,
            'prompt_ver': PROMPT_VERSION,
            'parser_ver': PARSER_VERSION,
            'model': MODEL_NAME,
            'temp': TEMPERATURE,
            'top_p': TOP_P,
            'max_tok': MAX_TOKENS,
            'raw': g_raw,
            'norm_json': normalized_json,
            'raw_hash': raw_hash,
            'val_status': validation_status,
            'guidance_status': g_status,
            'upd': now,
        })

        if g_usage and not g_usage.get('cached'):
            conn.execute("""
                INSERT INTO llm_usage_log (ticker, earnings_date, extractor, model_name, prompt_hash,
                    prompt_version, parser_version,
                    temperature, top_p, max_tokens,
                    prompt_tokens, completion_tokens, total_tokens,
                    input_chars, output_chars,
                    latency_ms, processing_time_seconds, cost_estimate,
                    input_price, output_price,
                    retries_used, cached, response_id, finish_reason)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (ticker, ed, 'guidance', MODEL_NAME, GUIDANCE_PROMPT_HASH,
                  PROMPT_VERSION, PARSER_VERSION,
                  TEMPERATURE, TOP_P, MAX_TOKENS,
                  g_usage['prompt_tokens'], g_usage['completion_tokens'], g_usage['total_tokens'],
                  g_usage['input_chars'], g_usage['output_chars'],
                  g_usage['latency_ms'], elapsed, g_usage['cost'],
                  INPUT_PRICE_PER_1M, OUTPUT_PRICE_PER_1M,
                  g_usage['retries_used'], 0,
                  g_usage.get('response_id'), g_usage.get('finish_reason')))

    if rt_parsed:
        rt = rt_parsed
        risks = _get_section(rt, 'risks')
        rt_raw_hash = _compute_raw_hash(rt_raw) if rt_raw else None
        rt_status = STATUS_CACHED if rt_usage and rt_usage.get('cached') else STATUS_DONE
        rt_normalized = _to_json(rt) if rt else None

        conn.execute("""
            INSERT INTO risks_llm (
                ticker, earnings_date, risks_present, risk_count,
                overall_risk_level, risks_json,
                document_hash, prompt_hash, prompt_version,
                parser_version, model_name,
                temperature, top_p, max_tokens,
                raw_response, normalized_json, raw_response_hash,
                risks_status, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT (ticker, earnings_date) DO UPDATE SET
                risks_present = excluded.risks_present,
                risk_count = excluded.risk_count,
                overall_risk_level = excluded.overall_risk_level,
                risks_json = excluded.risks_json,
                document_hash = excluded.document_hash,
                prompt_hash = excluded.prompt_hash,
                prompt_version = excluded.prompt_version,
                parser_version = excluded.parser_version,
                model_name = excluded.model_name,
                temperature = excluded.temperature,
                top_p = excluded.top_p,
                max_tokens = excluded.max_tokens,
                raw_response = excluded.raw_response,
                normalized_json = excluded.normalized_json,
                raw_response_hash = excluded.raw_response_hash,
                risks_status = excluded.risks_status,
                updated_at = excluded.updated_at
        """, (
            ticker, ed,
            1 if risks.get('risks_present') else 0,
            risks.get('risk_count', 0), risks.get('overall_risk_level', 'none'),
            _to_json(risks.get('risks', [])),
            content_hash, RISK_TONE_PROMPT_HASH, PROMPT_VERSION,
            PARSER_VERSION, MODEL_NAME,
            TEMPERATURE, TOP_P, MAX_TOKENS,
            rt_raw, rt_normalized, rt_raw_hash,
            rt_status, now
        ))
        tone = _get_section(rt, 'tone')
        conn.execute("""
            INSERT INTO tone_llm (
                ticker, earnings_date, tone_present,
                certainty, sentiment, language_markers, evidence,
                document_hash, prompt_hash, prompt_version,
                parser_version, model_name,
                temperature, top_p, max_tokens,
                raw_response, normalized_json, raw_response_hash,
                tone_status, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT (ticker, earnings_date) DO UPDATE SET
                tone_present = excluded.tone_present,
                certainty = excluded.certainty,
                sentiment = excluded.sentiment,
                language_markers = excluded.language_markers,
                evidence = excluded.evidence,
                document_hash = excluded.document_hash,
                prompt_hash = excluded.prompt_hash,
                prompt_version = excluded.prompt_version,
                parser_version = excluded.parser_version,
                model_name = excluded.model_name,
                temperature = excluded.temperature,
                top_p = excluded.top_p,
                max_tokens = excluded.max_tokens,
                raw_response = excluded.raw_response,
                normalized_json = excluded.normalized_json,
                raw_response_hash = excluded.raw_response_hash,
                tone_status = excluded.tone_status,
                updated_at = excluded.updated_at
        """, (
            ticker, ed,
            1 if tone.get('tone_present') else 0,
            tone.get('certainty', 'unknown'), tone.get('sentiment', 'unknown'),
            _to_json(tone.get('language_markers', [])), tone.get('evidence', ''),
            content_hash, RISK_TONE_PROMPT_HASH, PROMPT_VERSION,
            PARSER_VERSION, MODEL_NAME,
            TEMPERATURE, TOP_P, MAX_TOKENS,
            rt_raw, rt_normalized, rt_raw_hash,
            rt_status, now
        ))
        if rt_usage and not rt_usage.get('cached'):
            conn.execute("""
                INSERT INTO llm_usage_log (ticker, earnings_date, extractor, model_name, prompt_hash,
                    prompt_version, parser_version,
                    temperature, top_p, max_tokens,
                    prompt_tokens, completion_tokens, total_tokens,
                    input_chars, output_chars,
                    latency_ms, processing_time_seconds, cost_estimate,
                    input_price, output_price,
                    retries_used, cached, response_id, finish_reason)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (ticker, ed, 'risks_tone', MODEL_NAME, RISK_TONE_PROMPT_HASH,
                  PROMPT_VERSION, PARSER_VERSION,
                  TEMPERATURE, TOP_P, MAX_TOKENS,
                  rt_usage['prompt_tokens'], rt_usage['completion_tokens'], rt_usage['total_tokens'],
                  rt_usage['input_chars'], rt_usage['output_chars'],
                  rt_usage['latency_ms'], elapsed, rt_usage['cost'],
                  INPUT_PRICE_PER_1M, OUTPUT_PRICE_PER_1M,
                  rt_usage['retries_used'], 0,
                  rt_usage.get('response_id'), rt_usage.get('finish_reason')))


# ---------------------------------------------------------------------------
# Record failure – correctly tagged per extractor
# ---------------------------------------------------------------------------
_failure_buffer = []

def record_failure(ticker, ed, extractor, error, traceback_str, doc_hash=''):
    _failure_buffer.append((ticker, ed, extractor, str(error)[:500], (traceback_str or '')[:2000], doc_hash))


def flush_failures(conn):
    global _failure_buffer
    if not _failure_buffer:
        return
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    for ticker, ed, extractor, error_msg, tb_str, doc_hash in _failure_buffer:
        prompt_hash = GUIDANCE_PROMPT_HASH if extractor == 'guidance' else RISK_TONE_PROMPT_HASH
        conn.execute("""
            INSERT INTO failed_llm (ticker, earnings_date, extractor, model_name, prompt_hash, document_hash,
                error_message, error_traceback, attempts, last_attempt)
            VALUES (?,?,?,?,?,?,?,?,1,datetime('now'))
            ON CONFLICT (ticker, earnings_date, extractor) DO UPDATE SET
                model_name = excluded.model_name,
                prompt_hash = excluded.prompt_hash,
                document_hash = excluded.document_hash,
                attempts = attempts + 1,
                error_message = excluded.error_message,
                error_traceback = excluded.error_traceback,
                last_attempt = excluded.last_attempt
        """, (ticker, ed, extractor, MODEL_NAME, prompt_hash, doc_hash, error_msg, tb_str))
        if extractor == 'guidance':
            conn.execute("UPDATE guidance_llm SET guidance_status = ?, updated_at = ? WHERE ticker = ? AND earnings_date = ?", (STATUS_FAILED, now, ticker, ed))
        elif extractor == 'risks_tone':
            conn.execute("UPDATE risks_llm SET risks_status = ?, updated_at = ? WHERE ticker = ? AND earnings_date = ?", (STATUS_FAILED, now, ticker, ed))
            conn.execute("UPDATE tone_llm SET tone_status = ?, updated_at = ? WHERE ticker = ? AND earnings_date = ?", (STATUS_FAILED, now, ticker, ed))
    conn.commit()
    _failure_buffer = []


def mark_empty_as_failed(conn, ticker, ed):
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute("UPDATE guidance_llm SET guidance_status = ?, updated_at = ? WHERE ticker = ? AND earnings_date = ?", (STATUS_FAILED, now, ticker, ed))
    conn.execute("UPDATE risks_llm SET risks_status = ?, updated_at = ? WHERE ticker = ? AND earnings_date = ?", (STATUS_FAILED, now, ticker, ed))
    conn.execute("UPDATE tone_llm SET tone_status = ?, updated_at = ? WHERE ticker = ? AND earnings_date = ?", (STATUS_FAILED, now, ticker, ed))
    record_failure(ticker, ed, 'guidance', 'Empty paragraph or matched_sentence', '')


# ---------------------------------------------------------------------------
# Batch processor – atomically claims rows
# ---------------------------------------------------------------------------
def _reset_stale_processing(conn):
    threshold = (datetime.utcnow() - timedelta(minutes=STALE_PROCESSING_MINUTES)).strftime('%Y-%m-%d %H:%M:%S')
    for table, status_col in [('guidance_llm', 'guidance_status'), ('risks_llm', 'risks_status'), ('tone_llm', 'tone_status')]:
        conn.execute(f"UPDATE {table} SET {status_col} = ?, updated_at = datetime('now') WHERE {status_col} = ? AND updated_at < ?", (STATUS_FAILED, STATUS_PROCESSING, threshold))


def _extractor_already_done(conn, ticker, ed, extractor):
    if extractor == 'guidance':
        row = conn.execute("SELECT guidance_status FROM guidance_llm WHERE ticker=? AND earnings_date=?", (ticker, ed)).fetchone()
        return row and row[0] in (STATUS_DONE, STATUS_CACHED)
    elif extractor == 'risks_tone':
        r = conn.execute("SELECT risks_status FROM risks_llm WHERE ticker=? AND earnings_date=?", (ticker, ed)).fetchone()
        t = conn.execute("SELECT tone_status FROM tone_llm WHERE ticker=? AND earnings_date=?", (ticker, ed)).fetchone()
        return r and r[0] in (STATUS_DONE, STATUS_CACHED) and t and t[0] in (STATUS_DONE, STATUS_CACHED)
    return False


def process_batch(conn, batch_size=BATCH_SIZE):
    _reset_stale_processing(conn)
    stale_threshold = (datetime.utcnow() - timedelta(minutes=STALE_PROCESSING_MINUTES)).strftime('%Y-%m-%d %H:%M:%S')

    df = pd.read_sql("""
        SELECT g.ticker, g.earnings_date, g.label, g.matched_sentence, g.paragraph
        FROM guidance_datasetv2 g
        WHERE g.label IS NOT NULL AND g.label != 3
          AND (
              NOT EXISTS (SELECT 1 FROM guidance_llm gl WHERE gl.ticker = g.ticker AND gl.earnings_date = g.earnings_date AND gl.guidance_status IN (?, ?))
              OR NOT EXISTS (SELECT 1 FROM risks_llm rl WHERE rl.ticker = g.ticker AND rl.earnings_date = g.earnings_date AND rl.risks_status IN (?, ?))
              OR NOT EXISTS (SELECT 1 FROM tone_llm tl WHERE tl.ticker = g.ticker AND tl.earnings_date = g.earnings_date AND tl.tone_status IN (?, ?))
              OR EXISTS (SELECT 1 FROM guidance_llm gl2 WHERE gl2.ticker = g.ticker AND gl2.earnings_date = g.earnings_date AND gl2.guidance_status = ? AND gl2.updated_at < ?)
              OR EXISTS (SELECT 1 FROM risks_llm rl2 WHERE rl2.ticker = g.ticker AND rl2.earnings_date = g.earnings_date AND rl2.risks_status = ? AND rl2.updated_at < ?)
              OR EXISTS (SELECT 1 FROM tone_llm tl2 WHERE tl2.ticker = g.ticker AND tl2.earnings_date = g.earnings_date AND tl2.tone_status = ? AND tl2.updated_at < ?)
          )
        ORDER BY g.earnings_date ASC
        LIMIT ?
    """, conn, params=(STATUS_DONE, STATUS_CACHED, STATUS_DONE, STATUS_CACHED, STATUS_DONE, STATUS_CACHED,
                       STATUS_PROCESSING, stale_threshold, STATUS_PROCESSING, stale_threshold, STATUS_PROCESSING, stale_threshold, batch_size))

    if df.empty:
        logger.info("No pending or failed rows to process.")
        return 0

    logger.info(f"Processing {len(df)} rows...")
    processed = 0
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    for _, row in df.iterrows():
        conn.execute("""
            INSERT INTO guidance_llm (ticker, earnings_date, guidance_status, updated_at) VALUES (?,?,?,?)
            ON CONFLICT (ticker, earnings_date) DO UPDATE SET guidance_status = ?, updated_at = ?
        """, (row['ticker'], row['earnings_date'], STATUS_PROCESSING, now, STATUS_PROCESSING, now))
        conn.execute("""
            INSERT INTO risks_llm (ticker, earnings_date, risks_status, updated_at) VALUES (?,?,?,?)
            ON CONFLICT (ticker, earnings_date) DO UPDATE SET risks_status = ?, updated_at = ?
        """, (row['ticker'], row['earnings_date'], STATUS_PROCESSING, now, STATUS_PROCESSING, now))
        conn.execute("""
            INSERT INTO tone_llm (ticker, earnings_date, tone_status, updated_at) VALUES (?,?,?,?)
            ON CONFLICT (ticker, earnings_date) DO UPDATE SET tone_status = ?, updated_at = ?
        """, (row['ticker'], row['earnings_date'], STATUS_PROCESSING, now, STATUS_PROCESSING, now))
    conn.commit()

    try:
        conn.execute("BEGIN TRANSACTION")
        for _, row in df.iterrows():
            ticker = row['ticker']
            ed = row['earnings_date']
            rule_label = row['label']
            matched_sentence = row['matched_sentence'] or ''
            paragraph = row['paragraph'] or ''
            row_start_time = time.perf_counter()

            if not paragraph.strip() and not matched_sentence.strip():
                mark_empty_as_failed(conn, ticker, ed)
                processed += 1
                continue

            guidance_hash = compute_content_hash(paragraph, matched_sentence, 'guidance')
            risks_tone_hash = compute_content_hash(paragraph, matched_sentence, 'risks_tone')

            if not _extractor_already_done(conn, ticker, ed, 'guidance'):
                cached_g = lookup_cached_guidance(conn, guidance_hash)
                if cached_g:
                    g_parsed, g_raw, g_usage = cached_g
                else:
                    g_parsed, g_raw, g_usage, g_err, g_tb = extract_guidance_llm(paragraph, matched_sentence)
                    if g_parsed is None:
                        record_failure(ticker, ed, 'guidance', g_err or 'All retries or validation failed', g_tb, guidance_hash)
            else:
                g_parsed, g_raw, g_usage = None, None, None

            if not _extractor_already_done(conn, ticker, ed, 'risks_tone'):
                cached_rt = lookup_cached_risks_tone(conn, risks_tone_hash)
                if cached_rt:
                    rt_parsed, rt_raw, rt_usage = cached_rt
                else:
                    rt_parsed, rt_raw, rt_usage, rt_err, rt_tb = extract_risks_tone_llm(paragraph, matched_sentence)
                    if rt_parsed is None:
                        record_failure(ticker, ed, 'risks_tone', rt_err or 'All retries or validation failed', rt_tb, risks_tone_hash)
            else:
                rt_parsed, rt_raw, rt_usage = None, None, None

            store_all_results(conn, ticker, ed, rule_label,
                              g_parsed, g_raw, g_usage,
                              rt_parsed, rt_raw, rt_usage,
                              guidance_hash, row_start_time)

            processed += 1
            if processed % COMMIT_EVERY == 0:
                conn.commit()
                flush_failures(conn)
                conn.execute("BEGIN TRANSACTION")
                logger.info(f"  Committed {processed} rows...")

        conn.commit()
    except Exception as e:
        logger.error(f"  Batch error: {e}. Rolling back uncommitted rows.")
        conn.rollback()
        raise
    finally:
        if conn.in_transaction:
            try:
                conn.rollback()
            except:
                pass
        flush_failures(conn)

    logger.info(f"Batch complete. {processed} rows processed.")
    return processed


# ---------------------------------------------------------------------------
# Test / Run
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    create_all_tables(conn)

    df = pd.read_sql("""
        SELECT ticker, earnings_date, label, matched_sentence, paragraph
        FROM guidance_datasetv2
        WHERE ticker = 'BBY' AND label == 2 AND earnings_date = '2004-09-15'
    """, conn)

    if not df.empty:
        row = df.iloc[0]
        ticker, ed, rule_label = row['ticker'], row['earnings_date'], row['label']
        matched_sentence = row['matched_sentence'] or ''
        paragraph = row['paragraph'] or ''
        content_hash = compute_content_hash(paragraph, matched_sentence, 'guidance')

        logger.info(f"=== Testing {ticker} ({ed}) ===")
        g_parsed, g_raw, g_usage, g_err, g_tb = extract_guidance_llm(paragraph, matched_sentence)
        rt_parsed, rt_raw, rt_usage, rt_err, rt_tb = extract_risks_tone_llm(paragraph, matched_sentence)

        if g_parsed:
            logger.info("\nGuidance:"); print(json.dumps(g_parsed, indent=2))
        if rt_parsed:
            logger.info("\nRisks & Tone:"); print(json.dumps(rt_parsed, indent=2))

        store_all_results(conn, ticker, ed, rule_label,
                          g_parsed, g_raw, g_usage,
                          rt_parsed, rt_raw, rt_usage,
                          content_hash, time.perf_counter())
        flush_failures(conn)
        logger.info("✓ Stored.")
    else:
        logger.info("No test row. Running batch mode...")
        process_batch(conn)

    conn.close()
    logger.info("Done.")