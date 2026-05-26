# sqlite3 – Python's Built‑in Library for SQLite Databases

## What is sqlite3?
`sqlite3` is a **Python library** that lets your scripts talk to **SQLite** database files. It comes pre‑installed with Python – you never need to run `pip install`.  
SQLite itself is a lightweight, file‑based database. Think of it as a powerful spreadsheet stored in a single file on your computer.

Your Earnings Catalyst Screener will use `sqlite3` to store everything: stock symbols, price history, filter results, and trade logs.

## Why SQLite?
- No separate server to install or maintain.
- The entire database is one file (e.g., `data/universe.db`).
- Perfect for single‑user, local analysis – exactly what you need.
- Python's `sqlite3` module makes it easy: connect → execute SQL → commit → close.

## Core Workflow (Every Script)
Every script that talks to SQLite follows the same four steps:

```python
import sqlite3

# 1. Connect (creates the database file if it doesn't exist)
conn = sqlite3.connect('path/to/database.db')
c = conn.cursor()         # get a "cursor" to send commands

# 2. Execute SQL commands (CREATE TABLE, INSERT, SELECT, etc.)
c.execute('''CREATE TABLE IF NOT EXISTS ...''')

# 3. Save changes (if you made any changes)
conn.commit()

# 4. Close the connection
conn.close()
```
## Key Methods
`sqlite3.connect(filename)`
Opens (or creates) the database file. Returns a connection object.

`connection.cursor()`
Returns a cursor object – your tool to run SQL commands.

`cursor.execute(sql, params)`
Sends a SQL command to the database.

The first argument is the SQL string.
The second (optional) argument is a tuple of values to safely insert.
```
c.execute("SELECT * FROM ticker_master")
c.execute("INSERT INTO ticker_master VALUES (?, ?)", ("AAPL", "Apple Inc."))
```
`connection.commit()`
Saves all changes permanently to the file. If you forget to commit, your data will be lost when the script ends.

`connection.close()`
Closes the connection. Good practice to free resources.

## Reading Data
`cursor.fetchall()`
Returns a list of all remaining rows from the last SELECT.

Using `fetchall()`
```python
c.execute("SELECT * FROM ticker_master")
all_rows = c.fetchall()
print(all_rows)
# Output: [('PEP', 'PepsiCo'), ('TSM', 'Taiwan Semiconductor'), ('GS', 'Goldman Sachs')]
```
`cursor.fetchone()`
Returns the next row (as a tuple) or None.

Using `fetchone()`
```python
c.execute("SELECT * FROM ticker_master")
first_row = c.fetchone()
print(first_row)      # ('PEP', 'PepsiCo')

second_row = c.fetchone()
print(second_row)     # ('TSM', 'Taiwan Semiconductor')

third_row = c.fetchone()
print(third_row)      # ('GS', 'Goldman Sachs')

fourth_row = c.fetchone()
print(fourth_row)     # None (no more rows)
```

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

## Inserting Data
Use INSERT OR REPLACE to avoid duplicate‑key errors:
```c.execute("INSERT OR REPLACE INTO ticker_master VALUES (?, ?)", ("PEP", "PepsiCo"))
```
**Always use ? placeholders – never insert values directly into the SQL string (security risk).**

```python
import sqlite3

conn = sqlite3.connect('data.db')
c = conn.cursor

# to create the table for the first time
c.execute("""
CREATE TABLE IF NOT EXISTS data (
first text, second text, last text, number integer, float_number real)
""")

#to insert new data with values
c.execute("INSERT INTO data values (?, ?, ?, ?, ?)", ('hi', 'test', 'yay', 1, 50.802))

#you can also use dictionaries 
c.execute("INSERT INTO data values (:first, :second, :last, :number, :float_number)", {'first':'hi', 'second':'test', 'last':'yay', 'number':1, 'float_number':50.802})

#select certain data from a database
c.execute("SELECT * FROM data WHERE last='yay'")
c.execute("SELECT * FROM data WHERE last=?", ('yay', 'etc'))

c.fetchone() # to return just the next row as a tuple, the same its inserted
c.fetchmany(integer) #return a list of tuples that fullfil the criteria
c.fetchall() # same like c.fetchmany() but it returns all


conn.commit()
conn.close()
```