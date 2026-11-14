# RetailMind V4.3 — Airflow orchestration (local demo)

The manually triggered `retailmind_v4_spark_dbt_pipeline` DAG runs four
idempotent stages: deterministic synthetic generation (seed 42) -> PySpark
cleaning into Parquet -> dbt staging/marts and SQL tests -> Python reconciliation
of DuckDB against the source. Any failed step prevents downstream execution.

## Architecture and isolation

- Airflow 2.10.5 runs its scheduler and UI in its original Python environment.
- Java 17 and a separate `/opt/retailmind-venv` hold PySpark 4.0.5,
  dbt Core 1.12.7, dbt-duckdb 1.11.1 and DuckDB 1.5.6.
- `RETAILMIND_HOME=/opt/airflow/project`, matching the bind-mounted source.
- `retailmind_airflow_data` is mounted on `/opt/airflow/project/data`; it **masks**
  the host `data/` directory inside the Airflow container. Neither the V3
  SQLite warehouse nor local ML files are overwritten.
- The existing V3 DAG and other Compose services remain available.
- A one-off `airflow-data-init` service (root only for initialization) gives the
  Airflow UID 50000 write access to the isolated V4 volume before startup.
- dbt runs with `--no-partial-parse`, Docker-specific compile/log paths under
  `data/dbt_target_airflow/` and `data/dbt_logs_airflow/`, avoiding reuse
  of artifacts produced by dbt on Windows under the bind-mounted `dbt/`.
- Local only: Airflow is bound to `127.0.0.1:8080`, uses SequentialExecutor,
  and is not a hardened production deployment.

## Windows PowerShell (repository root)

```powershell
# Validate the new DAG without needing Airflow installed on Windows.
.\.venv\Scripts\python.exe -m pytest tests/test_airflow_v4.py -v

# Parse and build the optional Airflow image (this may download large packages).
docker compose --profile airflow config --quiet
docker compose --profile airflow build airflow

# Validate Java/Python/dbt before starting the web UI.
docker compose --profile airflow run --rm --no-deps airflow bash -lc 'java -version && /opt/retailmind-venv/bin/python -c "import pyspark, duckdb; print(pyspark.__version__, duckdb.__version__)" && /opt/retailmind-venv/bin/dbt --version'

# Start Airflow only; do not start the V3 bootstrap/API services.
docker compose --profile airflow up -d airflow

# Validate DAG import then trigger it manually through the UI or CLI.
docker compose --profile airflow exec airflow airflow dags list-import-errors
docker compose --profile airflow exec airflow airflow dags trigger retailmind_v4_spark_dbt_pipeline

# Follow startup logs or use http://localhost:8080 for the task graph and logs.
docker compose --profile airflow logs -f airflow
```

The existing local-only demo credentials are defined in `docker-compose.yml`.
Do not expose port 8080 publicly or reuse demo credentials in a shared environment.

### Expected local checks after a successful DAG run

- PySpark source rows: 5,025; unique curated rows: 5,000.
- Synthetic anomaly flags: 334.
- Paid revenue: 4,003,524.57 MAD.
- dbt: 3 models and 10 tests; Python verifier: `status=passed` with
  `daily_mismatches=0` and `region_mismatches=0`.

These are **expected** figures from the seeded fixture, not proof that the
container/DAG has been executed. Capture real run logs before claiming success.

## Recovery when dbt was previously blocked

If the DAG task failed with `dbt_duckdb://macros/flights.sql`, update this
DAG and clear only `dbt_build_marts_and_tests` and downstream tasks in
Airflow. Previous successful generate/Spark steps need not rerun.

A changed Compose config may recreate the container upon next `up -d`;
the named Airflow metadata volume and V4 data volume persist.
Never use `down --volumes` for this recovery.

## Stop safely

```powershell
docker compose --profile airflow stop airflow
```

Do **not** run `docker compose down --volumes`: that would delete persistent
local state, including data from other Compose services.
