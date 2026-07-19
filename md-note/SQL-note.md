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

SELECT DISTINCT sector FROM companies;
/* if you only want the unique values */

SELECT * FROM ticker_master WHERE earnings_date BETWEEN '2025-01-01' AND '2025-06-30'

SELECT * FROM ticker_master WHERE ticker IN ('AAPL','MSFT','GOOG')
-- to filter for tickers: AAPL or MSFT or GOOG
```

## Pattern Matching
```sql
-- Starts with A
SELECT * FROM ticker_master WHERE ticker LIKE 'A%'

-- Ends with A
SELECT * FROM ticker_master WHERE ticker LIKE '%A'

-- Contains APP
SELECT * FROM ticker_master WHERE ticker LIKE '%APP%'
```

## Aliasing
`SELECT column_name AS alias_name FROM table_name`
this if for replacing the column name 
`SELECT column_name FROM table_name AS alias_name
this is for replaceing the table name`

## Joining
imagine we have this data

companies
| company_id | ticker |
| :--------- | :----- |
|     1      |  AAPL  |
|     2      |  MSFT  |

earnings
| company_id |  EPS   |
| :--------- | :----- |
|     1      |  2.50  |
|     2      |  3.10  |
### Inner Join
Only matching rows.
```sql
SELECT *
FROM companies c
JOIN earnings e
ON c.company_id=e.company_id;
```
| ticker |  EPS   |
| :----- | :----- |
|  AAPL  |  2.50  |
|  MSFT  |  3.10  |

### Left Join
Keeps everything from the left table.
Missing matches become NULL.
Very useful.

### Right Join
Keeps everything from the right table.

### Full Outer Join
Keeps everything from both tables.

## Common Aggregate functions
- COUNT()
- SUM()
- AVG()
- MIN()
- MAX()

## Subquery
```sql
SELECT *
FROM companies
WHERE market_cap >
(
SELECT AVG(market_cap)
FROM companies
);
```

## Common Table Expression (CTE)
```sql
WITH tech AS
(
SELECT *
FROM companies
WHERE sector='Tech'
)

SELECT *
FROM tech;
```

## Set Operators
### `UNION`
combine to SELECT with no duplicates
```sql
SELECT ticker
FROM tech_companies
WHERE ticker IN ('AAPL','MSFT')
-- AAPL
-- MSFT
UNION

SELECT ticker
FROM tech_companies
WHERE ticker IN ('MSFT','GOOG');
-- MSFT
-- GOOG

-- Output:
/*
AAPL
MSFT
GOOG

*/
```

### `UNION ALL`
same like `UNION` but it keeps the dulpicates.

### `INTERSECT`
This means "Give me only rows that exist in BOTH queries".

## `EXCEPT`
This means "Give me everything in Query 1 that is NOT in Query 2."