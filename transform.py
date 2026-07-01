"""
transform.py
TRANSFORM step of the ETL pipeline.

Reads uncategorized rows from transactions_raw, classifies each transaction
into a spending category using keyword matching against the description,
and writes the cleaned, categorized rows into transactions_clean.

Categorization is rule-based (keyword matching) rather than ML — this keeps
the pipeline dependency-free and fully explainable for a hackathon demo,
which matters more than model sophistication at this stage.

Usage:
    python transform.py --db data/output/finance.db
"""

import argparse
import sqlite3

# Keyword -> category rules. Checked in order, first match wins.
# Keywords are matched case-insensitively against the transaction description.
CATEGORY_RULES = [
    ("Groceries", ["checkers", "pick n pay", "woolworths food", "shoprite", "spar"]),
    ("Eating Out", ["mugg", "kfc", "steers", "nando", "uber eats", "wimpy", "debonairs"]),
    ("Transport", ["uber trip", "shell", "engen", "gautrain", "bolt", "taxi", "fuel"]),
    ("Airtime & Data", ["vodacom", "mtn", "telkom", "cell c", "airtime", "data bundle"]),
    ("Subscriptions", ["netflix", "dstv", "spotify", "showmax", "amazon prime", "apple.com"]),
    ("Rent/Housing", ["rent payment", "rent ", "landlord", "bond payment"]),
    ("Utilities", ["city power", "joburg water", "eskom", "municipal", "electricity"]),
    ("Insurance", ["discovery", "outsurance", "momentum", "old mutual", "insurance", "medical aid"]),
    ("Entertainment", ["ster-kinekor", "sun international", "spur family", "cinema", "casino"]),
    ("Shopping", ["mr price", "edgars", "takealot", "game stores", "woolworths fashion", "h&m"]),
    ("Bank Fees", ["account fee", "atm withdrawal fee", "card replacement", "service fee"]),
    ("Savings Transfer", ["eft to savings", "savings account", "investment transfer"]),
    ("Income", ["salary", "employer", "deposit received"]),
]


def categorize(description):
    desc_lower = description.lower()
    for category, keywords in CATEGORY_RULES:
        if any(kw in desc_lower for kw in keywords):
            return category
    return "Other / Uncategorized"


def transform(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id, txn_date, description, amount FROM transactions_raw")
    raw_rows = cur.fetchall()

    clean_rows = []
    for raw_id, txn_date, description, amount in raw_rows:
        month = txn_date[:7]  # YYYY-MM
        category = categorize(description)
        txn_type = "credit" if amount > 0 else "debit"
        clean_rows.append((raw_id, txn_date, month, description, category, amount, txn_type))

    # Clear previous run's clean data to keep transform idempotent
    cur.execute("DELETE FROM transactions_clean")
    cur.executemany(
        """
        INSERT INTO transactions_clean (raw_id, txn_date, month, description, category, amount, txn_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        clean_rows,
    )
    conn.commit()
    conn.close()
    return len(clean_rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/output/finance.db", help="Path to SQLite DB")
    args = parser.parse_args()

    n = transform(args.db)
    print(f"[TRANSFORM] Categorized {n} transactions")


if __name__ == "__main__":
    main()
