"""V4.5 snapshot contract, safe export and bounded read-only API tests."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from retailmind.v4_monitoring import read_snapshot, router
from scripts import export_v4_monitoring as exporter

RUN = {
    "dag_id": exporter.DAG_ID,
    "run_id": "manual__2026-11-14T21:49:59+00:00",
    "state": "success",
    "execution_date": "2026-11-14T21:49:59+00:00",
    "start_date": "2026-11-14T23:22:09.713407+00:00",
    "end_date": "2026-11-14T23:23:15.347988+00:00",
}
TASKS = [
    {"task_id": "generate_synthetic_transactions", "state": "success",
     "start_date": "2026-11-14T23:22:12.996030+00:00", "end_date": "2026-11-14T23:22:13.508758+00:00"},
    {"task_id": "spark_etl_to_parquet", "state": "success",
     "start_date": "2026-11-14T23:22:17.539783+00:00", "end_date": "2026-11-14T23:22:52.428036+00:00"},
    {"task_id": "dbt_build_marts_and_tests", "state": "success",
     "start_date": "2026-11-14T23:22:56.959880+00:00", "end_date": "2026-11-14T23:23:08.950329+00:00"},
    {"task_id": "verify_dbt_vs_spark", "state": "success",
     "start_date": "2026-11-14T23:23:13.318663+00:00", "end_date": "2026-11-14T23:23:14.741690+00:00"},
]
METRICS = {
    "source": "pyspark_parquet", "warehouse": "duckdb_dbt", "transactions": 5000,
    "injected_anomalies": 334, "paid_revenue_mad": 4003524.57,
    "daily_mismatches": 0, "region_mismatches": 0, "status": "passed",
}


def cli_stub(*args):
    if args[0:3] == ("airflow", "dags", "list-runs"):
        return [RUN]
    if args[0:3] == ("airflow", "tasks", "states-for-dag-run"):
        return TASKS
    if args[0].endswith("/python"):
        return METRICS
    raise AssertionError(f"Unexpected CLI: {args}")


def test_real_log_shape_and_durations(monkeypatch):
    monkeypatch.setattr(exporter, "docker_json", cli_stub)
    data = exporter.export_snapshot()
    assert data["source"] == "airflow_cli_snapshot" and data["live"] is False
    assert data["runs"][0]["duration_seconds"] == 65.635
    assert [task["task_id"] for task in data["runs"][0]["tasks"]] == [task["task_id"] for task in TASKS]
    assert data["runs"][0]["tasks"][1]["duration_seconds"] == 34.888
    assert data["data_metrics"] == METRICS


def test_no_live_data_is_not_fabricated(monkeypatch):
    def stub(*args):
        if args[0:3] == ("airflow", "dags", "list-runs"):
            return []
        return cli_stub(*args)
    monkeypatch.setattr(exporter, "docker_json", stub)
    data = exporter.export_snapshot(with_data=False)
    assert data["runs"] == [] and data["data_metrics"] is None


def test_reject_unexpected_run_id(monkeypatch):
    def stub(*args):
        if args[0:3] == ("airflow", "dags", "list-runs"):
            return [{**RUN, "run_id": "--bad"}]
        return cli_stub(*args)
    monkeypatch.setattr(exporter, "docker_json", stub)
    with pytest.raises(exporter.ExportError):
        exporter.export_snapshot()


def test_reject_failed_data_contract(monkeypatch):
    def stub(*args):
        if args[0].endswith("/python"):
            return {**METRICS, "status": "failed"}
        return cli_stub(*args)
    monkeypatch.setattr(exporter, "docker_json", stub)
    with pytest.raises(exporter.ExportError):
        exporter.export_snapshot()


def test_snapshot_write_and_read(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(exporter, "docker_json", cli_stub)
    path = tmp_path / "monitoring" / "v4_pipeline.json"
    data = exporter.export_snapshot()
    exporter.write_snapshot(data, path)
    assert read_snapshot(path)["runs"][0]["state"] == "success"
    assert not list(path.parent.glob("*.tmp"))


def test_missing_or_corrupt_snapshot_is_503(tmp_path: Path):
    from fastapi import HTTPException
    path = tmp_path / "missing.json"
    with pytest.raises(HTTPException) as error:
        read_snapshot(path)
    assert error.value.status_code == 503
    path.write_text('{"schema_version": 999}', encoding="utf-8")
    with pytest.raises(HTTPException):
        read_snapshot(path)


def test_oversized_file_is_rejected(tmp_path: Path):
    from fastapi import HTTPException
    path = tmp_path / "bad.json"
    path.write_text("x" * (256 * 1024 + 1), encoding="utf-8")
    with pytest.raises(HTTPException) as error:
        read_snapshot(path)
    assert error.value.status_code == 503


def test_router_is_read_only(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(exporter, "docker_json", cli_stub)
    path = tmp_path / "monitoring.json"
    exporter.write_snapshot(exporter.export_snapshot(), path)
    monkeypatch.setenv("RETAILMIND_MONITORING_SNAPSHOT", str(path))
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    response = client.get("/v4/monitoring")
    assert response.status_code == 200
    assert response.json()["runs"][0]["tasks"][2]["state"] == "success"
    assert client.post("/v4/monitoring").status_code == 405
    path.unlink()
    assert client.get("/v4/monitoring").status_code == 503
