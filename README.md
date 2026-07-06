# SpendSense — Bank Statement ETL & Savings Advisor

A minimum-viable ETL pipeline that takes a person's bank statement (3–6
months), categorizes every transaction, and generates plain-English
insights about where they're overspending and how much they could
realistically save — like a lightweight, automated financial advisor.

Built for a WTC_elective demo: small footprint, no external paid APIs,
runs entirely on mock or real CSV data.

## How it works (30 second version)

```
CSV bank statement
      |
      v
  [EXTRACT]  -- raw rows land untouched in SQLite
      |
      v
  [TRANSFORM] -- each transaction categorized via keyword rules
      |             (Groceries, Transport, Eating Out, Subscriptions, ...)
      v
  [LOAD/ANALYZE] -- spend aggregated by month + category,
      |              rule-based "financial advisor" logic generates
      |              savings tips, exports summary.json
      v
  Frontend (HTML/CSS/JS) -- visualizes spend breakdown + savings tips
```

Airflow orchestrates the three pipeline stages as a DAG
(`extract -> transform -> load_and_analyze`). The frontend is a fully
standalone HTML file that can also parse a CSV directly in-browser
(same categorization logic, duplicated in JS) — so you can demo the
visualization instantly without waiting on Docker/Airflow if needed.

## Project structure

```
bankstatement-etl/
├── dags/
│   └── bank_statement_etl_dag.py   # Airflow DAG: orchestrates the 3 stages
├── scripts/
│   ├── extract.py                  # CSV -> raw SQLite table
│   ├── transform.py                # categorize transactions
│   ├── load.py                     # aggregate + generate savings insights + JSON export
│   └── generate_mock_data.py       # creates a realistic mock 3-month statement
├── sql/
│   └── schema.sql                  # SQLite table definitions
├── frontend/
│   └── index.html                  # upload CSV -> visualize spend + tips (standalone)
├── data/
│   ├── uploads/                    # input CSVs land here
│   └── output/                     # finance.db + summary.json land here
├── Dockerfile                      # Airflow image + our scripts
├── docker-compose.yml              # postgres + airflow + frontend containers
├── requirements.txt
├── run.sh                    # run the pipeline without Docker, for fast iteration
└── README.md
```

## Option A — Run with Docker (full pipeline, Airflow UI)

Requires Docker and Docker Compose.

```bash
docker compose up --build
```

This starts four services:

| Service            | URL                     | Purpose                              |
|--------------------|--------------------------|---------------------------------------|
| airflow-webserver  | http://localhost:8080    | Trigger and monitor the DAG (login: `admin` / `admin`) |
| airflow-scheduler  | (background)             | Runs the DAG                          |
| postgres           | (internal only)          | Airflow's own metadata store          |
| frontend           | http://localhost:8081    | Upload-and-visualize web app          |

**To run the pipeline:**
1. Drop a CSV into `data/uploads/` (or use the auto-generated mock data — see below)
2. Open http://localhost:8080, find the `bank_statement_etl` DAG, click the play button to trigger it
3. Once it succeeds, `data/output/summary.json` and `data/output/finance.db` are populated
4. Open http://localhost:8081 and drag in the same CSV to see the visual report

> Note: the Docker pipeline writes results to disk; the frontend re-parses
> the CSV client-side rather than reading `summary.json` directly, so the
> demo works identically whether Airflow ran or not. This was a deliberate
> "minimum" choice — no API server needed to bridge the two.

## Option B — Run locally without Docker (fastest for development)

Requires Python 3.9+.

```bash
./run.sh
```

This auto-generates a mock 3-month statement if none exists, then runs
extract → transform → load directly. Then open `frontend/index.html` in
any browser and drag in `data/uploads/mock_statement.csv`.

To use your own CSV:
```bash
./run.sh path/to/your_statement.csv
```

## CSV format expected

```csv
date,description,amount,balance
2026-04-01,Woolworths Food,-999.90,5500.10
2026-04-02,Checkers Sandton,-770.02,4730.08
2026-04-25,Salary - Employer Inc,18500.00,23230.08
```

- `amount`: negative = money out, positive = money in
- `balance`: optional, not currently used in analysis
- Categorization is keyword-based against `description` — see
  `scripts/transform.py` (`CATEGORY_RULES`) to add your own bank's
  merchant naming conventions

## Generating mock data manually

```bash
python3 scripts/mock_data.py --months 6 --out data/uploads/mock_6mo.csv
```

## Design decisions (why it's built this way)

- **SQLite, not Postgres, for the financial data**: zero extra container,
  file-based, trivial to inspect (`sqlite3 data/output/finance.db`) —
  appropriate for an MVP where a single user's data is processed at a time.
- **Keyword-based categorization, not ML**: fully explainable, zero
  training data needed, runs instantly, easy to extend by editing one
  list of rules. Good enough for a hackathon demo; an obvious "next step"
  to mention if asked about future work.
- **No backend API for the frontend**: the frontend parses CSVs directly
  in-browser using the same categorization rules as the Python pipeline.
  This keeps the "minimum" footprint the brief asked for — one less
  service to run, deploy, or explain — while keeping the Airflow pipeline
  as the "real" data engineering artifact for judges to inspect.
- **Rule-based "advisor" logic, not an LLM**: deterministic, free to run,
  and transparent — every insight in `load.py` traces to a specific,
  explainable rule (e.g. "discretionary category >15% of spend").

## Extending this

- Add more category rules in `scripts/transform.py` and the matching
  block in `frontend/index.html`'s `CATEGORY_RULES`.
- Swap the mock data generator for a real bank statement PDF parser
  (e.g. `pdfplumber`) if real statements are needed.
- Schedule the DAG (`schedule=None` → a cron string) for automatic
  monthly runs if statements are uploaded on a recurring basis.
- Swap rule-based insights for an LLM call (e.g. Gemini, since this
  pairs well with an EdTech/Google-hackathon stack) for more
  natural-language, personalized advice.
