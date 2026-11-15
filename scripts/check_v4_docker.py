"""Read-only V4 Docker/Airflow smoke checks (except one removed temp write probe).

Run from Windows or Linux after ``docker compose --profile airflow up -d airflow``.
Never starts a DAG, deletes a volume or modifies the V3 pipeline.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ("docker", "compose", "--profile", "airflow")
DAG_ID = "retailmind_v4_spark_dbt_pipeline"
PYTHON = "/opt/retailmind-venv/bin/python"
EXPECTED = {
    "status": "passed",
    "transactions": 5000,
    "injected_anomalies": 334,
    "paid_revenue_mad": 4003524.57,
    "daily_mismatches": 0,
    "region_mismatches": 0,
}


class SmokeCheckError(RuntimeError):
    """A local Docker preflight check did not pass."""


def command(*args: str) -> str:
    """Invoke Docker directly: argument lists avoid nested PowerShell/Bash quoting."""
    try:
        proc = subprocess.run(
            args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            errors="replace", check=False, timeout=90,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SmokeCheckError(f"Docker command unavailable or timed out: {args[0]} ({exc})") from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip()[-1400:]
        raise SmokeCheckError(f"Command failed ({proc.returncode}): {' '.join(args)}\n{detail}")
    return proc.stdout.strip()


def in_airflow(*args: str) -> str:
    return command(*COMPOSE, "exec", "-T", "airflow", *args)


def parse_json_output(output: str) -> dict:
    """Require JSON; never treat a warning or textual log as a successful report."""
    try:
        result = json.loads(output)
    except (json.JSONDecodeError, TypeError) as exc:
        raise SmokeCheckError(f"Expected JSON report; received: {output[-400:]}") from exc
    if not isinstance(result, dict):
        raise SmokeCheckError("JSON report must be an object")
    return result


def check(*, check_data: bool = False) -> dict:
    command(*COMPOSE, "config", "--quiet")

    container_id = command(*COMPOSE, "ps", "-q", "airflow").strip()
    if not container_id:
        raise SmokeCheckError("Airflow is not running. Use: docker compose --profile airflow up -d airflow")
    health = command("docker", "inspect", "--format", "{{.State.Health.Status}}", container_id)
    if health != "healthy":
        raise SmokeCheckError(
            f"Airflow health is '{health}', not 'healthy'. Run 'docker compose --profile airflow up -d airflow' "
            "after applying this patch, then inspect 'docker compose --profile airflow ps airflow'."
        )

    imports = in_airflow("airflow", "dags", "list-import-errors")
    if "No data found" not in imports:
        raise SmokeCheckError(f"Airflow DAG import errors: {imports[-1200:]}")
    dag_list = in_airflow("airflow", "dags", "list")
    if DAG_ID not in dag_list:
        raise SmokeCheckError(f"DAG not loaded: {DAG_ID}")

    versions = parse_json_output(in_airflow(
        PYTHON, "-c",
        "import json,pyspark,duckdb; print(json.dumps({'pyspark':pyspark.__version__,'duckdb':duckdb.__version__}))",
    ))
    if versions != {"pyspark": "4.0.5", "duckdb": "1.5.6"}:
        raise SmokeCheckError(f"V4 runtime dependency versions differ: {versions}")

    dbt_version = in_airflow("/opt/retailmind-venv/bin/dbt", "--version")
    if "1.12.7" not in dbt_version or "duckdb: 1.11.1" not in dbt_version:
        raise SmokeCheckError(f"dbt versions differ from V4 image: {dbt_version[-900:]}")

    # Probe the *isolated* V4 named volume, not the host's V3 data directory.
    write_check = in_airflow(
        PYTHON, "-c",
        "import tempfile; f=tempfile.NamedTemporaryFile(dir='/opt/airflow/project/data'); "
        "f.close(); print('WRITE_OK')",
    )
    if write_check != "WRITE_OK":
        raise SmokeCheckError(f"Cannot verify write permissions on V4 data volume: {write_check}")

    report = {
        "service": "airflow",
        "health": health,
        "dag_id": DAG_ID,
        "dag_imports": "passed",
        "versions": {**versions, "dbt_core": "1.12.7", "dbt_duckdb": "1.11.1"},
        "v4_volume_write": "passed",
        "data_contract": "not_checked",
        "status": "passed",
    }
    if check_data:
        data = parse_json_output(in_airflow(
            PYTHON, "/opt/airflow/project/scripts/verify_dbt.py", "--root", "/opt/airflow/project",
        ))
        actual = {name: data.get(name) for name in EXPECTED}
        if actual != EXPECTED:
            raise SmokeCheckError(f"V4 dataset contract failed: {actual}")
        report["data_contract"] = "passed"
        report["data_metrics"] = data
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Check RetailMind V4 Airflow Docker readiness")
    parser.add_argument("--check-data", action="store_true", help="Also verify the seeded V4 DuckDB data contract")
    parser.add_argument("--output", type=Path, help="Optional local JSON report (e.g. data/reports/v4_docker.json)")
    args = parser.parse_args()
    try:
        report = check(check_data=args.check_data)
    except SmokeCheckError as exc:
        print(f"V4 Docker smoke check FAILED: {exc}", file=sys.stderr)
        return 1
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    print(payload, end="")
    if args.output is not None:
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
