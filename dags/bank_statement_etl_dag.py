"""
bank_statement_etl_dag.py

Airflow DAG that orchestrates the bank statement ETL pipeline:

    extract  ->  transform  ->  load_and_analyze

Each task shells out to the corresponding script in /opt/airflow/scripts
(mounted from ./scripts on the host). This keeps the DAG itself thin —
it's an orchestration layer, not where business logic lives — which makes
the pipeline easier to test (you can run extract.py / transform.py /
load.py directly without Airflow at all) and easier to explain in a demo.

Trigger manually from the Airflow UI, or drop a new CSV into
data/uploads/ and trigger the DAG with that filename as a config param.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

SCRIPTS_DIR = "/opt/airflow/scripts"
DB_PATH = "/opt/airflow/data/output/finance.db"
JSON_OUT = "/opt/airflow/data/output/summary.json"
DEFAULT_INPUT = "/opt/airflow/data/uploads/mock_statement.csv"

default_args = {
    "owner": "spendsense",
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
        dag_id="bank_statement_etl",
        description="Extract, categorize, and analyze a bank statement to surface savings insights",
        default_args=default_args,
        schedule=None,  # manual trigger for the wtc demo; set a cron string to run automatically
        start_date=datetime(2026, 1, 1),
        catchup=False,
        tags=["finance", "etl", "wtc"],
        params={"input_file": DEFAULT_INPUT},
) as dag:

    extract_task = BashOperator(
        task_id="extract",
        bash_command=(
            f"python {SCRIPTS_DIR}/extract.py "
            f"--input {{{{ params.input_file }}}} "
            f"--db {DB_PATH}"
        ),
    )

    transform_task = BashOperator(
        task_id="transform",
        bash_command=f"python {SCRIPTS_DIR}/transform.py --db {DB_PATH}",
    )

    load_task = BashOperator(
        task_id="load_and_analyze",
        bash_command=(
            f"python {SCRIPTS_DIR}/load.py "
            f"--db {DB_PATH} "
            f"--json-out {JSON_OUT}"
        ),
    )

    extract_task >> transform_task >> load_task
