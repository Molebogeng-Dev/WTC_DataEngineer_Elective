"""
mock_data.py
Generates a realistic mock 3-month bank statement CSV for a South African
individual, used to test the ETL pipeline end to end without needing a
real bank export.

Usage:
    python mock_data.py --months 3 --out data/uploads/mock_statement.csv
"""

import argparse
import csv
import random
from datetime import date, timedelta

random.seed(42)

# Realistic SA merchant-style descriptions per category.
# Amounts are ZAR. Negative = money out (debit), positive = money in (credit).
MERCHANTS = {
    "Groceries": ["Checkers Sandton", "Pick n Pay", "Woolworths Food", "Shoprite"],
    "Eating Out": ["Mugg & Bean", "KFC Drive Thru", "Steers", "Nando's", "Uber Eats"],
    "Transport": ["Uber Trip", "Shell Garage Fuel", "Engen Fuel", "Gautrain Top-up"],
    "Airtime & Data": ["Vodacom Prepaid", "MTN Airtime", "Telkom Data Bundle"],
    "Subscriptions": ["Netflix", "DSTV Now", "Spotify Premium", "Showmax"],
    "Rent/Housing": ["Rent Payment - Landlord"],
    "Utilities": ["City Power Prepaid", "Joburg Water", "Eskom Prepaid"],
    "Insurance": ["Discovery Health Premium", "OUTsurance Car Cover"],
    "Entertainment": ["Ster-Kinekor", "Sun International", "Spur Family"],
    "Shopping": ["Mr Price", "Edgars", "Takealot.com", "Game Stores"],
    "Bank Fees": ["Monthly Account Fee", "ATM Withdrawal Fee", "Card Replacement Fee"],
    "Savings Transfer": ["EFT to Savings Account"],
}

CATEGORY_RANGES = {
    "Groceries": (150, 1200),
    "Eating Out": (60, 450),
    "Transport": (100, 800),
    "Airtime & Data": (50, 300),
    "Subscriptions": (99, 199),
    "Rent/Housing": (4500, 4500),
    "Utilities": (300, 900),
    "Insurance": (450, 1100),
    "Entertainment": (100, 600),
    "Shopping": (150, 2000),
    "Bank Fees": (8, 95),
    "Savings Transfer": (500, 1500),
}

# Roughly how many transactions per category per month
CATEGORY_FREQUENCY = {
    "Groceries": 8,
    "Eating Out": 10,
    "Transport": 12,
    "Airtime & Data": 2,
    "Subscriptions": 3,
    "Rent/Housing": 1,
    "Utilities": 3,
    "Insurance": 2,
    "Entertainment": 3,
    "Shopping": 4,
    "Bank Fees": 3,
    "Savings Transfer": 1,
}

SALARY = 18500.00


def random_day(year, month):
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    days_in_month = (next_month - date(year, month, 1)).days
    return date(year, month, random.randint(1, days_in_month))


def generate(months):
    today = date.today()
    rows , period = [], [] 
    balance = 6500.00  
    y, m = today.year, today.month
    for _ in range(months):
        period.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    period.reverse()

    for (yr, mo) in period:
        # Salary credit on the 25th (or last available day)
        salary_day = min(25, 28)
        txn_date = date(yr, mo, salary_day)
        balance += SALARY
        rows.append([txn_date.isoformat(), "Salary - Employer Inc", round(SALARY, 2), round(balance, 2)])

        # Spending transactions
        for category, count in CATEGORY_FREQUENCY.items():
            low, high = CATEGORY_RANGES[category]
            for _ in range(count):
                merchant = random.choice(MERCHANTS[category])
                amount = round(-random.uniform(low, high), 2)
                txn_date = random_day(yr, mo)
                balance += amount
                rows.append([txn_date.isoformat(), merchant, amount, round(balance, 2)])

    # Sort  running balance properly
    rows.sort(key=lambda r: r[0])
    running = 6500.00
    final_rows = []
    for txn_date, desc, amount, _ in rows:
        running += amount
        final_rows.append([txn_date, desc, amount, round(running, 2)])

    return final_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", type=int, default=3)
    parser.add_argument("--out", type=str, default="data/uploads/mock_statement.csv")
    args = parser.parse_args()

    rows = generate(args.months)

    with open(args.out, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "description", "amount", "balance"])
        writer.writerows(rows)

    print(f"Generated {len(rows)} transactions across {args.months} months -> {args.out}")


if __name__ == "__main__":
    main()
