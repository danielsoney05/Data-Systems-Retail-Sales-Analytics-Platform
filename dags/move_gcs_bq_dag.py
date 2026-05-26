from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime
import pendulum

local_tz = pendulum.timezone("Australia/Sydney")

with DAG(
    dag_id="move_gcs_bq_daily",
    start_date=datetime(2026, 5, 6, tzinfo=local_tz),
    schedule="45 23 * * *",
    catchup=False,
    tags=["gcs", "bigquery"],
) as dag:

    run_gcs_bq_script = BashOperator(
        task_id="run_gcs_bq_script",
        bash_command="cd /opt/airflow/project && python pipeline/move_gcs_bq.py",
    )