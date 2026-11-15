"""Read-only API for a separately exported, explicitly timestamped Airflow snapshot.

No Docker socket, Airflow password, or live scheduler access is exposed to FastAPI.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

from retailmind.settings import ROOT

router = APIRouter(prefix="/v4", tags=["V4 monitoring"])
SNAPSHOT_NAME = "v4_pipeline.json"
MAX_SNAPSHOT_BYTES = 256 * 1024


def read_snapshot(path: Path) -> dict:
    """Read only a bounded V4 snapshot, returning a clear 503 when unavailable."""
    try:
        if path.stat().st_size > MAX_SNAPSHOT_BYTES:
            raise ValueError("Snapshot too large")
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1:
            raise ValueError("Unsupported snapshot format")
        if snapshot.get("dag_id") != "retailmind_v4_spark_dbt_pipeline":
            raise ValueError("Unexpected DAG")
        if not isinstance(snapshot.get("runs"), list) or not isinstance(snapshot.get("captured_at"), str):
            raise ValueError("Missing monitoring fields")
        return snapshot
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Monitoring V4 indisponible. Exporter le snapshot Airflow depuis le PC avec "
                   "scripts/export_v4_monitoring.py.",
        ) from exc


@router.get("/monitoring")
def monitoring():
    path = Path(os.environ.get("RETAILMIND_MONITORING_SNAPSHOT", str(ROOT / "monitoring" / SNAPSHOT_NAME)))
    return read_snapshot(path)
