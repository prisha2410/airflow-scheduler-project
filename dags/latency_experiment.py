from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timezone

def record_latency(**context):
    scheduled_at = context['data_interval_start']
    actual_start = datetime.now(timezone.utc)
    lag = (actual_start - scheduled_at).total_seconds()
    print(f"SCHEDULING_LAG_SECONDS={lag:.2f}")
    print(f"Scheduled for: {scheduled_at}")
    print(f"Actually started: {actual_start}")

with DAG(
    dag_id='latency_experiment',
    schedule='* * * * *',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['experiment']
) as dag:
    PythonOperator(
        task_id='measure_latency',
        python_callable=record_latency,
    )
