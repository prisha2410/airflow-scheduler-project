
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG("dag_47", schedule=None, start_date=datetime(2024,1,1), catchup=False) as dag:
    BashOperator(task_id="t1", bash_command="echo 47")
