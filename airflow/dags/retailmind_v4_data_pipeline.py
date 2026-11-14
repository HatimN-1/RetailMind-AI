"""V4.3: manually triggered, isolated synthetic-data PySpark -> dbt DAG.

The V3 API/SQLite/ML pipeline remains unchanged. Compose mounts V4's data
on an independent named volume at /opt/airflow/project/data.
"""
from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT = "/opt/airflow/project"
PYTHON = "/opt/retailmind-venv/bin/python"
DBT = "/opt/retailmind-venv/bin/dbt"

with DAG(
    dag_id="retailmind_v4_spark_dbt_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule=None,  # Explicit manual trigger; never regenerate automatically.
    catchup=False,
    tags=["retailmind", "v4", "synthetic", "spark", "dbt"],
    default_args={"retries": 1},
) as dag:
    generate = BashOperator(
        task_id="generate_synthetic_transactions",
        bash_command=f"cd {PROJECT} && {PYTHON} -m retailmind.generate --rows 5000 --seed 42",
    )
    spark = BashOperator(
        task_id="spark_etl_to_parquet",
        bash_command=f"cd {PROJECT} && {PYTHON} -m retailmind.spark_etl --master 'local[2]'",
    )
    build = BashOperator(
        task_id="dbt_build_marts_and_tests",
        bash_command=(
            f"mkdir -p {PROJECT}/data/marts && cd {PROJECT}/dbt "
            f"&& {DBT} build --project-dir . --profiles-dir . "
            f"--no-partial-parse "
            f"--target-path {PROJECT}/data/dbt_target_airflow "
            f"--log-path {PROJECT}/data/dbt_logs_airflow"
        ),
    )
    verify = BashOperator(
        task_id="verify_dbt_vs_spark",
        bash_command=(
            f"cd {PROJECT}/dbt && {PYTHON} {PROJECT}/scripts/verify_dbt.py --root {PROJECT}"
        ),
    )

    generate >> spark >> build >> verify
