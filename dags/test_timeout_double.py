from datetime import timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago

with DAG(
    "test_timeout_double",
    start_date=days_ago(1),
    schedule_interval=None,
    dagrun_timeout=timedelta(seconds=20),
    catchup=False,
) as dag:
    BashOperator(task_id="slow_task", bash_command="sleep 60")
