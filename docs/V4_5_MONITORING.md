# RetailMind AI V4.5 — Airflow monitoring snapshot in React

This stage deliberately **does not expose Docker or Airflow credentials to the browser**.
The Windows host reads Airflow's real CLI JSON, writes an atomic snapshot,
FastAPI returns only that file via `GET /v4/monitoring`, and React visualizes it.

## Architecture / limitations

1. Airflow 2.10.5 stays under Docker Compose (`127.0.0.1:8080`).
2. The operator **manually** runs `scripts/export_v4_monitoring.py` on the host.
3. The script reads up to 10 real DAG runs, their task states/durations and optionally
   rechecks the existing DuckDB-Parquet data contract. It does **not** trigger a DAG.
4. It writes `monitoring/v4_pipeline.json` atomically. Generated snapshots are ignored by Git.
5. FastAPI reads the bounded JSON and responds on `GET /v4/monitoring`; it has no
   Docker socket access, no Airflow API credentials and no write/refresh endpoint.
6. React displays run history, task durations, data metrics and the capture time.

**This is operator-refreshed historical monitoring, not real-time monitoring.**
The UI's refresh button re-reads the snapshot and does not contact Airflow.
An old snapshot remains old even while the Airflow service is running.

## Windows PowerShell — from repository root

```powershell
# Verify Airflow is up (and healthy) and export fresh real status/data.
docker compose --profile airflow ps airflow
.\.venv\Scripts\python.exe scripts/export_v4_monitoring.py

# Read FastAPI endpoint from a local server after starting V3 FastAPI:
# powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_api_windows.ps1
Invoke-RestMethod http://127.0.0.1:8000/v4/monitoring | ConvertTo-Json -Depth 8

# React dev mode (separate terminal): cd frontend; npm.cmd run dev
# Open http://127.0.0.1:5173 and click « Pipelines V4 ».
```

When using **Docker Compose V3 API**, the read-only `./monitoring:/app/monitoring:ro`
mount exposes the same snapshot to the API service. Rebuild/recreate the API image
only when explicitly testing the Docker V3 API, and **do not use `down --volumes`**.

To export only task history, use `--skip-data`; the UI will correctly show
"Non mesurée" instead of inventing quality metrics.

## Tests / safety

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_v4_monitoring.py -v
.\.venv\Scripts\python.exe -m ruff check src tests scripts/export_v4_monitoring.py --select E4,E7,E9,F
cd frontend; npm.cmd run build
```

No client data or credentials are exported. All V4 transaction data are synthetic.
This does not change the V3 SQLite warehouse, ML models, existing API endpoints,
existing Airflow DAG, or the `main` branch.
