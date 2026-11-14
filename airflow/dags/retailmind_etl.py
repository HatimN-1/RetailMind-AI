"""Airflow DAG (optional service). No free LLM or Azure mutations are executed.
Airflow runs inside the optional airflow container defined in compose.
"""
from __future__ import annotations
from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator

BASE = "cd /opt/airflow/project && python -m "
with DAG(
    dag_id="retailmind_data_ml_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule=None,  # Manual triggers by design; prevents surprise reprocessing.
    catchup=False,
    tags=["portfolio", "synthetic", "data-eng", "ml"],
    default_args={"retries": 1},
) as dag:
    generate = BashOperator(task_id="generate_transactions", bash_command=BASE + "retailmind.generate --rows 5000")
    quality = BashOperator(task_id="quality_gated_etl", bash_command=BASE + "retailmind.etl")
    warehouse = BashOperator(task_id="build_warehouse", bash_command=BASE + "retailmind.warehouse")
    model = BashOperator(task_id="train_and_evaluate", bash_command=BASE + "retailmind.train")
    generate >> quality >> warehouse >> model
