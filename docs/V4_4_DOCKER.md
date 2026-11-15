# RetailMind V4.4.2 — Docker readiness and isolation (local demo)

The V4.3 DAG already ran end to end in Airflow. This stage adds **repeatable
readiness checks**, not a production deployment or a new pipeline. It does not
change the V3 FastAPI/SQLite/React/ML services and never triggers a DAG.

## What is verified

- Docker Compose parses without starting any V3 service.
- The V4 Airflow container is running and **healthy**: both Airflow's `/health`
  web endpoint and its scheduler job check must succeed.
- Airflow reports no DAG import errors and lists the V4 DAG.
- The isolated Airflow Python environment exposes pinned PySpark 4.0.5,
  DuckDB 1.5.6, dbt Core 1.12.7 and dbt-duckdb 1.11.1.
- Airflow UID 50000 can write to its **V4 named volume**, using a disposable
  temporary file that is immediately deleted.
- `--check-data` (optional) verifies an **already completed** seed-42 DAG run:
  5,000 transactions, 334 synthetic anomaly labels, 4,003,524.57 MAD paid
  revenue and no daily/region mismatches.

The checker prints a JSON summary; it does **not** start a DAG, create a
warehouse, delete data, expose secrets, or modify the V3 SQLite database.

## PowerShell — from repository root

```powershell
# 1. Syntax (also performed by the smoke script)
docker compose --profile airflow config --quiet

# 2. Apply the new Docker healthcheck to the existing service.
# Named volumes for Airflow metadata and V4 data are preserved.
docker compose --profile airflow up -d airflow

# 3. Inspect health; the final state should be "healthy".
docker compose --profile airflow ps airflow

# 4. Check Docker, the loaded DAG, versions and data-volume permissions.
.\.venv\Scripts\python.exe scripts/check_v4_docker.py

# 5. If the V4 DAG has finished successfully, check the seeded data contract.
.\.venv\Scripts\python.exe scripts/check_v4_docker.py --check-data --output data/reports/v4_docker_validation.json
```

On Windows, if `.env` starts with a UTF-8 BOM, Docker Compose may fail with
`unexpected character "\\ufeff"`. Rewrite **only that file's encoding** to
UTF-8 without BOM, keeping values unchanged. Never paste `.env` in a ticket.

The JSON output distinguishes `data_contract=not_checked` (readiness only)
from `data_contract=passed` (actual persisted data reconciled). Generated
reports and dbt targets/logs are ignored by Git.

## Verification in CI

The existing `.github/workflows/v4-data.yml` runs structural tests of this
checker and validates the Compose file. It already runs the real PySpark/dbt
DuckDB contract in a Linux runner; **this check does not claim to boot an
Airflow webserver in CI**. The Docker smoke script must also be run locally
against an actual Airflow container.

## Recovery and scope

- If the container has status `starting`, inspect `docker compose --profile
  airflow ps airflow` and the service logs. Do not trigger another DAG to fix
  a readiness problem.
- For `unhealthy`, inspect `docker compose --profile airflow logs --tail=120
  airflow` and verify both webserver and scheduler are alive.
- For a missing DAG, use `docker compose --profile airflow exec airflow
  airflow dags list-import-errors`.
- If the data contract fails, inspect the failed DAG task and do not delete
  its volumes or overwrite V3 assets.
- Stop safely with `docker compose --profile airflow stop airflow`.

**Never run `docker compose down --volumes` for troubleshooting**: it would
remove persistent Docker state. Airflow 2.10.5 uses a local SQLite metadata DB
and SequentialExecutor here; this is a single-machine demonstration, not a
production-grade Airflow deployment. The local demonstration credential must
not be reused or exposed publicly.
