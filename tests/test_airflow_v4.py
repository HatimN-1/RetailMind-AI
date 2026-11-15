"""Static and isolated DAG wiring checks; no Airflow/Docker install needed."""

from pathlib import Path
import runpy
import sys
import types


ROOT = Path(__file__).resolve().parents[1]


def test_airflow_v4_dag_wiring(monkeypatch):
    """Exercise the real DAG file against tiny Airflow API stubs."""
    tasks = {}
    edges = []
    dags = []

    class FakeDAG:
        def __init__(self, **kwargs):
            dags.append(kwargs)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    class FakeBashOperator:
        def __init__(self, task_id, bash_command):
            assert task_id not in tasks
            self.task_id = task_id
            tasks[task_id] = bash_command

        def __rshift__(self, other):
            edges.append((self.task_id, other.task_id))
            return other

    airflow = types.ModuleType("airflow")
    operators = types.ModuleType("airflow.operators")
    bash = types.ModuleType("airflow.operators.bash")
    airflow.DAG = FakeDAG
    bash.BashOperator = FakeBashOperator
    monkeypatch.setitem(sys.modules, "airflow", airflow)
    monkeypatch.setitem(sys.modules, "airflow.operators", operators)
    monkeypatch.setitem(sys.modules, "airflow.operators.bash", bash)

    runpy.run_path(str(ROOT / "airflow/dags/retailmind_v4_data_pipeline.py"))

    assert len(dags) == 1
    assert dags[0]["dag_id"] == "retailmind_v4_spark_dbt_pipeline"
    assert dags[0]["schedule"] is None
    assert dags[0]["catchup"] is False
    assert list(tasks) == [
        "generate_synthetic_transactions",
        "spark_etl_to_parquet",
        "dbt_build_marts_and_tests",
        "verify_dbt_vs_spark",
    ]
    assert edges == list(zip(list(tasks)[:-1], list(tasks)[1:]))
    assert "-m retailmind.generate --rows 5000 --seed 42" in tasks["generate_synthetic_transactions"]
    assert "-m retailmind.spark_etl --master 'local[2]'" in tasks["spark_etl_to_parquet"]
    assert "dbt build --project-dir . --profiles-dir ." in tasks["dbt_build_marts_and_tests"]
    dbt_task = tasks["dbt_build_marts_and_tests"]
    assert "--no-partial-parse" in dbt_task
    assert "--target-path /opt/airflow/project/data/dbt_target_airflow" in dbt_task
    assert "--log-path /opt/airflow/project/data/dbt_logs_airflow" in dbt_task
    assert "verify_dbt.py --root" in tasks["verify_dbt_vs_spark"]


def test_airflow_runtime_isolated_from_v3():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "docker/Dockerfile.airflow").read_text(encoding="utf-8")
    assert "retailmind_airflow_data:/opt/airflow/project/data" in compose
    assert "retailmind_airflow_data:/data" in compose
    assert "condition: service_completed_successfully" in compose
    assert "chown -R 50000:0 /data" in compose
    assert "RETAILMIND_HOME: /opt/airflow/project" in compose
    assert "PYSPARK_PYTHON: /opt/retailmind-venv/bin/python" in compose
    assert "openjdk-17-jre-headless" in dockerfile
    assert "python -m venv /opt/retailmind-venv" in dockerfile
    assert "dbt-duckdb==1.11.1" in dockerfile
    assert "pyspark==4.0.5" in dockerfile
