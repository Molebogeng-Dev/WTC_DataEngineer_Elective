FROM apache/airflow:2.9.3-python3.11

USER ROOT

USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Pipeline code
COPY dags/ /opt/airflow/dags/
COPY scripts/ /opt/airflow/scripts/
COPY sql/ /opt/airflow/sql/
