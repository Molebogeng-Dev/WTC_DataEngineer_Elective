"""
load.py
LOAD + ANALYZE step of the ETL pipeline.

Takes the categorized transactions in transactions_clean and:
  1. Aggregates spend by month and category -> category_summary table
  2. Runs simple rule-based "financial advisor" logic to generate savings
     insights -> insights table
  3. Exports a single JSON file the frontend reads directly (no API server
     needed for the MVP — keeps this "minimum" as requested).

Usage:
    python load.py --db data/output/finance.db --json-out data/output/summary.json
"""

import argparse
import json
import sqlite3
from collections import defaultdict

# Categories considered "discretionary" — i.e. realistic to cut back on.
# Rent, utilities, insurance and bank fees are mostly fixed/necessary so we
# don't suggest cutting those as a first recommendation.
DISCRETIONARY_CATEGORIES = {
    "Eating Out", "Entertainment", "Shopping", "Subscriptions", "Airtime & Data"
}

# Benchmark: flag a category as "high" if it exceeds this % of total monthly spend
HIGH_SPEND_THRESHOLD_PCT = 15.0


def build_summary(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT month, category, SUM(amount) as total, COUNT(*) as cnt
        FROM transactions_clean
        WHERE txn_type = 'debit'
        GROUP BY month, category
        ORDER BY month, total ASC
        """
    )
    rows = cur.fetchall()

    cur.execute("DELETE FROM category_summary")
    cur.executemany(
        "INSERT INTO category_summary (month, category, total_spent, txn_count) VALUES (?, ?, ?, ?)",
        [(m, c, abs(t), n) for m, c, t, n in rows],
    )
    conn.commit()

    # Build in-memory structures for insight generation
    by_month = defaultdict(lambda: defaultdict(float))
    overall_by_category = defaultdict(float)
    for month, category, total, _ in rows:
        spent = abs(total)
        by_month[month][category] = spent
        overall_by_category[category] += spent

    # Income per month (for savings rate calc)
    cur.execute(
        """
        SELECT month, SUM(amount) FROM transactions_clean
        WHERE txn_type = 'credit' GROUP BY month
        """
    )
    income_by_month = dict(cur.fetchall())

    conn.close()
    return by_month, overall_by_category, income_by_month


def generate_insights(by_month, overall_by_category, income_by_month, db_path):
    insights = []

    num_months = len(by_month) or 1
    avg_by_category = {cat: total / num_months for cat, total in overall_by_category.items()}
    total_avg_spend = sum(avg_by_category.values())
    avg_income = (sum(income_by_month.values()) / len(income_by_month)) if income_by_month else 0

    # 1. Top spending categories overall
    sorted_cats = sorted(avg_by_category.items(), key=lambda x: x[1], reverse=True)
    top_3 = sorted_cats[:3]
    for category, avg_spent in top_3:
        pct = (avg_spent / total_avg_spend * 100) if total_avg_spend else 0
        insights.append({
            "type": "summary",
            "category": category,
            "text": f"You spend an average of R{avg_spent:,.2f} per month on {category}, "
                    f"which is {pct:.1f}% of your total monthly spending.",
            "potential_saving": None,
        })

    # 2. Flag high discretionary spend with a concrete savings suggestion
    for category, avg_spent in sorted_cats:
        pct = (avg_spent / total_avg_spend * 100) if total_avg_spend else 0
        if category in DISCRETIONARY_CATEGORIES and pct >= HIGH_SPEND_THRESHOLD_PCT:
            suggested_cut = avg_spent * 0.30  # suggest cutting 30% of discretionary spend
            insights.append({
                "type": "saving_tip",
                "category": category,
                "text": f"Your {category} spend (R{avg_spent:,.2f}/month) is high relative to your "
                        f"overall budget. Cutting this by 30% could save you roughly "
                        f"R{suggested_cut:,.2f} per month, or R{suggested_cut * 12:,.2f} per year.",
                "potential_saving": round(suggested_cut, 2),
            })

    # 3. Subscriptions check — these are easy, low-effort cuts
    if "Subscriptions" in avg_by_category and avg_by_category["Subscriptions"] > 0:
        sub_spend = avg_by_category["Subscriptions"]
        insights.append({
            "type": "saving_tip",
            "category": "Subscriptions",
            "text": f"You're spending about R{sub_spend:,.2f}/month on subscriptions. Review which "
                    f"ones you actually use — cancelling even one unused subscription is the "
                    f"easiest saving available to you.",
            "potential_saving": round(sub_spend * 0.25, 2),
        })

    # 4. Savings rate insight
    if avg_income > 0:
        savings_transfer_avg = avg_by_category.get("Savings Transfer", 0)
        savings_rate = (savings_transfer_avg / avg_income) * 100
        if savings_rate < 10:
            target_saving = avg_income * 0.10
            gap = target_saving - savings_transfer_avg
            insights.append({
                "type": "warning",
                "category": "Savings Transfer",
                "text": f"You're currently saving about {savings_rate:.1f}% of your income. "
                        f"A common guideline is to save at least 10%. Increasing your monthly "
                        f"transfer to savings by R{gap:,.2f} would get you there.",
                "potential_saving": round(gap, 2),
            })
        else:
            insights.append({
                "type": "summary",
                "category": "Savings Transfer",
                "text": f"You're saving about {savings_rate:.1f}% of your income — solid habit, "
                        f"keep it up.",
                "potential_saving": None,
            })

    # 5. Eating out vs groceries ratio — common, very concrete SA budgeting tip
    eating_out = avg_by_category.get("Eating Out", 0)
    groceries = avg_by_category.get("Groceries", 0)
    if eating_out > 0 and groceries > 0 and eating_out > groceries * 0.5:
        insights.append({
            "type": "saving_tip",
            "category": "Eating Out",
            "text": f"You spend R{eating_out:,.2f}/month eating out compared to R{groceries:,.2f} "
                    f"on groceries. Shifting a few takeaway meals a week to home-cooked meals "
                    f"could realistically save you R{eating_out * 0.4:,.2f}/month.",
            "potential_saving": round(eating_out * 0.4, 2),
        })

    total_potential_saving = sum(i["potential_saving"] or 0 for i in insights)
    if total_potential_saving > 0:
        insights.insert(0, {
            "type": "summary",
            "category": None,
            "text": f"Based on your last {num_months} months of spending, you could realistically "
                    f"free up around R{total_potential_saving:,.2f} per month by acting on the "
                    f"tips below.",
            "potential_saving": round(total_potential_saving, 2),
        })

    # Persist to DB
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM insights")
    cur.executemany(
        "INSERT INTO insights (insight_text, insight_type, category, potential_saving) VALUES (?, ?, ?, ?)",
        [(i["text"], i["type"], i["category"], i["potential_saving"]) for i in insights],
    )
    conn.commit()
    conn.close()

    return insights


def export_json(by_month, overall_by_category, income_by_month, insights, json_out: str):
    months_sorted = sorted(by_month.keys())
    num_months = len(months_sorted) or 1
    avg_by_category = {cat: round(total / num_months, 2) for cat, total in overall_by_category.items()}

    payload = {
        "months_covered": months_sorted,
        "monthly_breakdown": {
            month: {cat: round(amt, 2) for cat, amt in cats.items()}
            for month, cats in by_month.items()
        },
        "average_monthly_by_category": avg_by_category,
        "average_monthly_income": round(sum(income_by_month.values()) / len(income_by_month), 2) if income_by_month else 0,
        "insights": insights,
    }

    import os
    os.makedirs(os.path.dirname(json_out), exist_ok=True)
    with open(json_out, "w") as f:
        json.dump(payload, f, indent=2)

    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/output/finance.db", help="Path to SQLite DB")
    parser.add_argument("--json-out", default="data/output/summary.json", help="Path to export JSON for frontend")
    args = parser.parse_args()

    by_month, overall_by_category, income_by_month = build_summary(args.db)
    insights = generate_insights(by_month, overall_by_category, income_by_month, args.db)
    payload = export_json(by_month, overall_by_category, income_by_month, insights, args.json_out)

    print(f"[LOAD] Wrote category summaries and {len(insights)} insights to {args.db}")
    print(f"[LOAD] Exported frontend JSON -> {args.json_out}")


if __name__ == "__main__":
    main()
