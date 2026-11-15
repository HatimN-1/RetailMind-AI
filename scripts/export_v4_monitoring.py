"""Export actual V4 Airflow CLI runs/tasks to an atomic, read-only API snapshot.

Run manually on the Docker host; never starts a DAG and never accesses V3 data.
The JSON is deliberately a snapshot, not real-time telemetry.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DAG_ID = "retailmind_v4_spark_dbt_pipeline"
COMPOSE = ("docker", "compose", "--profile", "airflow")
RUN_ID = re.compile(r"^[A-Za-z0-9_:+.\-]{1,240}$")
FIELDS = ("task_id", "state", "start_date", "end_date")
RUN_FIELDS = ("run_id", "state", "execution_date", "start_date", "end_date")
METRIC_FIELDS = ("source", "warehouse", "transactions", "injected_anomalies",
                 "paid_revenue_mad", "daily_mismatches", "region_mismatches", "status")


class ExportError(RuntimeError):
    """The source Airflow CLI was not available or returned invalid data."""


def docker_json(*command: str) -> object:
    argv = [*COMPOSE, "exec", "-T", "airflow", *command]
    try:
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExportError("Airflow inaccessible via Docker Compose") from exc
    if result.returncode:
        raise ExportError(f"Commande Airflow échouée : {(result.stderr or result.stdout).strip()[-700:]}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ExportError("Airflow n'a pas renvoyé de JSON valide") from exc


def duration_seconds(start: object, end: object) -> float | None:
    if not isinstance(start, str) or not isinstance(end, str):
        return None
    try:
        diff = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()
    except ValueError:
        return None
    return round(diff, 3) if diff >= 0 else None


def clean_row(row: object, allowed: tuple[str, ...]) -> dict:
    if not isinstance(row, dict):
        raise ExportError("Ligne JSON Airflow invalide")
    return {key: row.get(key) if isinstance(row.get(key), str) else None for key in allowed}


def export_snapshot(*, limit: int = 10, with_data: bool = True) -> dict:
    if not 1 <= limit <= 20:
        raise ExportError("La limite doit être comprise entre 1 et 20")
    raw_runs = docker_json("airflow", "dags", "list-runs", "-d", DAG_ID, "-o", "json")
    if not isinstance(raw_runs, list):
        raise ExportError("Liste des exécutions Airflow invalide")
    runs = []
    for raw_run in raw_runs[:limit]:
        run = clean_row(raw_run, RUN_FIELDS)
        run_id = run["run_id"]
        if not run_id or run_id.startswith("-") or not RUN_ID.fullmatch(run_id):
            raise ExportError("ID d'exécution Airflow inattendu")
        task_rows = docker_json("airflow", "tasks", "states-for-dag-run", DAG_ID, run_id, "-o", "json")
        if not isinstance(task_rows, list) or len(task_rows) > 200:
            raise ExportError("Liste des tâches Airflow invalide")
        tasks = []
        for raw_task in task_rows:
            task = clean_row(raw_task, FIELDS)
            task["duration_seconds"] = duration_seconds(task["start_date"], task["end_date"])
            tasks.append(task)
        run["duration_seconds"] = duration_seconds(run["start_date"], run["end_date"])
        run["tasks"] = tasks
        runs.append(run)
    metrics = None
    if with_data:
        raw_metrics = docker_json("/opt/retailmind-venv/bin/python",
                                  "/opt/airflow/project/scripts/verify_dbt.py",
                                  "--root", "/opt/airflow/project")
        if not isinstance(raw_metrics, dict) or raw_metrics.get("status") != "passed":
            raise ExportError("Le rapprochement PySpark/dbt n'a pas réussi")
        metrics = {field: raw_metrics.get(field) for field in METRIC_FIELDS}
    return {
        "schema_version": 1,
        "dag_id": DAG_ID,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": "airflow_cli_snapshot",
        "live": False,
        "runs": runs,
        "data_metrics": metrics,
    }


def write_snapshot(payload: dict, path: Path) -> None:
    """Write atomically: a failed collection never corrupts the previous snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".v4_snapshot_", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(serialized)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture Airflow V4 state for the read-only React dashboard")
    parser.add_argument("--limit", type=int, default=10, help="Maximum 20 recent DAG runs")
    parser.add_argument("--skip-data", action="store_true", help="Do not run DuckDB reconciliation")
    parser.add_argument("--output", type=Path, default=ROOT / "monitoring" / "v4_pipeline.json")
    args = parser.parse_args()
    try:
        snapshot = export_snapshot(limit=args.limit, with_data=not args.skip_data)
        write_snapshot(snapshot, args.output)
    except (ExportError, OSError, ValueError) as exc:
        print(f"Export monitoring V4 ÉCHOUÉ : {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": "passed", "snapshot": str(args.output),
                      "runs": len(snapshot["runs"]), "captured_at": snapshot["captured_at"],
                      "data_metrics": snapshot["data_metrics"] is not None}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
