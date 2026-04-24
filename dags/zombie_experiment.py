from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os
import signal
import time

def die_mid_task(**context):
    print("Task started - will simulate worker crash in 10 seconds")
    time.sleep(10)
    print("Simulating worker crash now!")
    os.kill(os.getpid(), signal.SIGKILL)  # hard kill - no cleanup

def normal_task(**context):
    print("I am a normal task running fine")
    time.sleep(5)
    print("Normal task completed successfully")

with DAG(
    dag_id='zombie_experiment',
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['experiment']
) as dag:

    normal = PythonOperator(
        task_id='normal_task',
        python_callable=normal_task,
    )

    zombie = PythonOperator(
        task_id='zombie_task',
        python_callable=die_mid_task,
        retries=0,
    )

    normal >> zombie
