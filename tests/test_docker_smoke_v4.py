"""V4.4.2 smoke command checks; Docker is mocked and never started by pytest."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("check_v4_docker", ROOT / "scripts" / "check_v4_docker.py")
assert SPEC and SPEC.loader
SMOKE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SMOKE)


def fake_docker_output(command):
    """Simulate a running, healthy Docker service and successful data contract."""
    args = list(command)
    if args[-2:] == ["config", "--quiet"]:
        return ""
    if args[-3:] == ["ps", "-q", "airflow"]:
        return "airflow-container-id"
    if args[:2] == ["docker", "inspect"]:
        return "healthy"
    if args[-2:] == ["dags", "list-import-errors"]:
        return "No data found"
    if args[-2:] == ["dags", "list"]:
        return "retailmind_v4_spark_dbt_pipeline | ..."
    if args[-2:] == ["dbt", "--version"] or args[-1:] == ["--version"]:
        return "Core:\n  - installed: 1.12.7\nPlugins:\n  - duckdb: 1.11.1"
    if args[-1] == "-c" or "-c" in args:
        code = args[-1]
        if "pyspark.__version__" in code:
            return json.dumps({"pyspark": "4.0.5", "duckdb": "1.5.6"})
        if "NamedTemporaryFile" in code:
            return "WRITE_OK"
    if any(str(item).endswith("/verify_dbt.py") for item in args):
        return json.dumps({
            "source": "pyspark_parquet", "warehouse": "duckdb_dbt",
            "status": "passed", "transactions": 5000,
            "injected_anomalies": 334, "paid_revenue_mad": 4003524.57,
            "daily_mismatches": 0, "region_mismatches": 0,
        })
    raise AssertionError(f"Unexpected Docker invocation: {args}")


def test_smoke_checks_health_dag_versions_and_writable_volume(monkeypatch):
    calls = []

    def command(*args):
        calls.append(args)
        return fake_docker_output(args)

    monkeypatch.setattr(SMOKE, "command", command)
    result = SMOKE.check()
    assert result["status"] == "passed"
    assert result["health"] == "healthy"
    assert result["v4_volume_write"] == "passed"
    assert result["data_contract"] == "not_checked"
    assert any("list-import-errors" in args for args in calls)
    assert not any(any(str(item).endswith("/verify_dbt.py") for item in args) for args in calls)


def test_smoke_checks_seeded_data_when_requested(monkeypatch):
    monkeypatch.setattr(SMOKE, "command", lambda *args: fake_docker_output(args))
    result = SMOKE.check(check_data=True)
    assert result["status"] == result["data_contract"] == "passed"
    assert result["data_metrics"]["transactions"] == 5000
    assert result["data_metrics"]["daily_mismatches"] == 0


def test_smoke_rejects_unhealthy_container(monkeypatch):
    def bad_health(*args):
        if args[:2] == ("docker", "inspect"):
            return "starting"
        return fake_docker_output(args)

    monkeypatch.setattr(SMOKE, "command", bad_health)
    with pytest.raises(SMOKE.SmokeCheckError, match="health is 'starting'"):
        SMOKE.check()


def test_smoke_rejects_wrong_data_contract(monkeypatch):
    def bad_contract(*args):
        if any(str(item).endswith("/verify_dbt.py") for item in args):
            payload = json.loads(fake_docker_output(args))
            payload["transactions"] = 4999
            return json.dumps(payload)
        return fake_docker_output(args)

    monkeypatch.setattr(SMOKE, "command", bad_contract)
    with pytest.raises(SMOKE.SmokeCheckError, match="dataset contract failed"):
        SMOKE.check(check_data=True)


def test_smoke_rejects_malformed_json():
    with pytest.raises(SMOKE.SmokeCheckError, match="Expected JSON"):
        SMOKE.parse_json_output("not JSON")


def test_compose_healthcheck_checks_web_and_scheduler():
    import yaml

    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    health = compose["services"]["airflow"]["healthcheck"]
    command = health["test"][1]
    assert "http://localhost:8080/health" in command
    assert "airflow jobs check --job-type SchedulerJob" in command
    assert "$$" in command  # Compose must not interpolate HOSTNAME on the host.
    assert compose["services"]["airflow"]["depends_on"]["airflow-data-init"]["condition"] == "service_completed_successfully"
