# SQL – The Language of Databases

## What is SQL?
**SQL** (Structured Query Language) is the standard language for talking to relational databases.
You don't need a separate server – your project uses SQLite, which understands SQL, and you send SQL commands via Python's `sqlite3` library.

Everything you store (tickers, price history, filters, trades) will be created, read, and managed with SQL.

## The Big Four (All You Need Right Now)

| Command | What It Does | Example |
| :--- | :--- | :--- |
| `SELECT` | Reads data | `SELECT * FROM ticker_master;` |
| `INSERT` | Adds new rows | `INSERT INTO ticker_master VALUES ('AAPL', 'Apple Inc.');` |
| `CREATE TABLE` | Creates a new table | `CREATE TABLE test (id INTEGER);` |
| `WHERE` | Filters rows | `SELECT * FROM ticker_master WHERE ticker='PEP';` |

## Creating Tables
```sql
CREATE TABLE IF NOT EXISTS price_history (
    ticker TEXT,
    date TEXT,
    close_price REAL,
    volume INTEGER,
    PRIMARY KEY (ticker, date)
);
```
- REAL = decimal number
- INTEGER = whole number
- PRIMARY KEY = unique combination, prevents duplicates
### Visual example
| ticker | date       | close_price | volume   |
| :---   | :---       | :---        | :---     |
| PEP    | 2024‑05‑10 | 153.20      | 4 500 000 |
| PEP    | 2024‑05‑11 | 154.10      | 5 200 000 |
| TSM    | 2024‑05‑10 | 366.00      | 8 900 000 |

## Filtering and Sorting
```sql
SELECT * FROM price_history WHERE ticker='PEP' AND date > '2024-01-01';

SELECT * FROM ticker_master ORDER BY company_name; 
/*Show me every row from ticker_master, sorted alphabetically by the company name (A → Z).*/

SELECT * FROM ticker_master ORDER BY ticker DESC; 
/*Show me every row from ticker_master, sorted by the ticker symbol in reverse alphabetical order (Z to A).*/
```

