"""
extract.py
EXTRACT step of the ETL pipeline.

Reads a raw CSV bank statement (date, description, amount, balance) and
loads it, unmodified, into the transactions_raw table in SQLite. This is
the "land the raw data" step — no cleaning or categorization happens here,
so the pipeline always keeps an untouched copy of what was uploaded.

Usage:
    python extract.py --input data/uploads/mock_statement.csv --db data/output/finance.db
"""

import argparse
import csv
import os
import sqlite3


def get_connection(db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sql", "schema.sql")
    with open(schema_path, "r") as f:
        conn.executescript(f.read())
    return conn


def extract(input_csv, db_path)
    conn = get_connection(db_path)
    cur = conn.cursor()

    with open(input_csv, "r") as f:
        reader = csv.DictReader(f)
        rows = [
            (
                row["date"].strip(),
                row["description"].strip(),
                float(row["amount"]),
                float(row["balance"]) if row.get("balance") not in (None, "") else None,
                os.path.basename(input_csv),
            )
            for row in reader
        ]

    cur.executemany(
        """
        INSERT INTO transactions_raw (txn_date, description, amount, balance, source_file)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    conn.close()
    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to raw CSV bank statement")
    parser.add_argument("--db", default="data/output/finance.db", help="Path to SQLite DB")
    args = parser.parse_args()

    n = extract(args.input, args.db)
    print(f"[EXTRACT] Loaded {n} raw transactions from {args.input} into {args.db}")


if __name__ == "__main__":
    main()
