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


## V4.5.2 — Historical runs, filters, operator refresh

- Airflow runs are sorted by actual UTC `execution_date` (newest first),
  duplicate run IDs are ignored, and up to 20 distinct runs are exported.
  Task order follows the four-step DAG even when Airflow's CLI lists tasks differently.
- React filters *Tous / Réussis / Échecs / En cours*, preserves the user's run
  selection when possible, and re-reads the **existing JSON** every 60 seconds.
  It never calls Docker or triggers/retries a DAG from the browser.
- The data contract is the **warehouse's state at capture time**, not a
  per-run dataset result. Selecting an older run does not change its metrics.
- A stale capture is explicitly labeled. Auto-reloading the file does **not**
  make Airflow data more recent; the operator must export again.

From PowerShell at the repo root (no new DAG is created):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\refresh_v4_monitoring_windows.ps1
# Optional: maximum 20 historical runs, without rechecking DuckDB:
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\refresh_v4_monitoring_windows.ps1 -Limit 20 -SkipData
```

When demonstrating history with multiple runs, use the **Airflow UI** to trigger
another execution *only if you explicitly want to regenerate the isolated V4
synthetic dataset*. Once that run is complete, execute the refresh command.
Do not delete volumes, modify the V3 warehouse, or claim automatic live updates.

Validation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_v4_monitoring.py -v
.\.venv\Scripts\python.exe -m ruff check src tests scripts/export_v4_monitoring.py --select E4,E7,E9,F
npm.cmd --prefix .\frontend run build
```
