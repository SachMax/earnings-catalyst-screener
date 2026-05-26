import sqlite3
import pandas as pd
from datetime import date, timedelta
import edgar
import yfinance as yf
import time
import google.genai
import json
from google.genai import types
from app.config import GEMINI_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY
import openai
from groq import Groq
import re
client = Groq(api_key=GROQ_API_KEY)
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


def extract_guidance_with_llm(text):
    prompt = f"""
You are a financial analyst assistant. Analyze the following 8‑K earnings press release text.
Return a JSON object with these keys:
- "guidance_type": one of "raise", "affirm", "first_time", "none"
- "eps_range": a list of two numbers [low, high] representing the EPS guidance range, or null
- "revenue_range": a list of two numbers [low, high] representing the revenue guidance range, or null (in millions)
- "confidence": your confidence in the extraction (0.0 to 1.0)

Use these rules:
- If the text explicitly says the company "affirms", "reaffirms", "reiterates", or "maintains" its prior financial guidance (even without new numbers), set "guidance_type" to "affirm" and leave the ranges null.
- If the text provides a numeric range or point estimate for future EPS or revenue that is *new or increased*, set "guidance_type" to "raise". If it is the first time the company gives an outlook, set it to "first_time". Extract the numbers into eps_range or revenue_range.
- If no guidance whatsoever is present, set "guidance_type" to "none" and leave the ranges null.

Text:
{text}
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )

        raw = response.choices[0].message.content.strip()

        # Extract JSON from code block or raw text
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
        if json_match:
            raw = json_match.group(1)
        else:
            start = raw.find('{')
            end = raw.rfind('}')
            if start != -1 and end != -1 and start < end:
                raw = raw[start:end+1]
            else:
                raise ValueError("No JSON object found in response")

        result = json.loads(raw)
        return result

    except Exception as e:
        print(f"  LLM error: {e}")
        return None
    
for index, row in df_ed.iterrows():
    ticker = row['ticker']
    ed_clean = row['earnings_date'].date()
    print(f"\n--- Processing {ticker} ---")   # new diagnostic

    try:
        stock = yf.Ticker(ticker)
        earnings_hist = stock.earnings_dates
        reported = earnings_hist[earnings_hist['Reported EPS'].notna()]
        if reported.empty:
            print(f"{ticker}: no reported earnings, skipping")
            continue
        last_report_date = reported.index[0].date()
        print(f"  Last report date: {last_report_date}")
    except Exception as e:
        print(f"{ticker}: error getting earnings history – {e}")
        continue

    # … filing search …
    start = last_report_date - timedelta(days=4)
    end   = last_report_date + timedelta(days=4)
    try:
        company = edgar.Company(ticker)
        filings = company.get_filings(form="8-K", filing_date=f"{start}:{end}")
        time.sleep(0.3)
    except Exception as e:
        print(f"{ticker}: error getting filings – {e}")
        continue

    guidance_valid = None
    for f in filings:
        try:
            text = f.text()
        except:
            continue

        result = extract_guidance_with_llm(text)
        if result is None:
            print(f"  Gemini returned None")
            continue
        guidance_type = result.get('guidance_type', 'none')
        print(f"  LLM response: {result}")   # always print the full result
        if guidance_type != 'none':
            if guidance_type in ("raise", "first_time"):
                guidance_valid = 1
            elif guidance_type == "affirm":
                guidance_valid = 0
            break   # stop after first non‑none guidance

    print(f"{ticker}: final guidance_valid = {guidance_valid}")

    c.execute("UPDATE features SET guidance_valid = ? WHERE ticker = ? AND earnings_date = ?",
              (guidance_valid, ticker, ed_clean.strftime("%Y-%m-%d")))
    conn.commit()
conn.close()