-- Bank Statement ETL — SQLite schema
-- Minimal, 3 tables: raw transactions, categorized transactions, summary

CREATE TABLE IF NOT EXISTS transactions_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_date TEXT NOT NULL,
    description TEXT NOT NULL,
    amount REAL NOT NULL,           -- negative = money out, positive = money in
    balance REAL,
    source_file TEXT,
    loaded_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS transactions_clean (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    raw_id INTEGER REFERENCES transactions_raw(id),
    txn_date TEXT NOT NULL,
    month TEXT NOT NULL,            -- YYYY-MM, used for monthly grouping
    description TEXT NOT NULL,
    category TEXT NOT NULL,         -- e.g. Groceries, Transport, Eating Out
    amount REAL NOT NULL,
    txn_type TEXT NOT NULL          -- 'debit' or 'credit'
);

CREATE TABLE IF NOT EXISTS category_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL,
    category TEXT NOT NULL,
    total_spent REAL NOT NULL,
    txn_count INTEGER NOT NULL,
    generated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    insight_text TEXT NOT NULL,
    insight_type TEXT NOT NULL,     -- 'saving_tip', 'warning', 'summary'
    category TEXT,
    potential_saving REAL,
    generated_at TEXT DEFAULT (datetime('now'))
);
