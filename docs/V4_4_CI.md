# RetailMind V4.4.1 — GitHub Actions data engineering gate

The optional `RetailMind V4 data pipeline` workflow adds a **real Linux PySpark
→ dbt → DuckDB integration check** alongside the existing V3 Python and React
workflows. It runs when the affected files change on pushes or pull requests.

## What runs

1. An isolated Ubuntu 24.04 runner installs Python 3.11, Temurin Java 17,
   PySpark 4.0.5, PyArrow 24.0.0, dbt Core 1.12.7, dbt-duckdb 1.11.1 and
   DuckDB 1.5.6.
2. Docker Compose is parsed without starting any containers.
3. Synthetic transactions are generated from seed 42 (5,000 unique rows).
4. PySpark produces the cleaned Parquet dataset.
5. dbt builds three DuckDB models and runs ten SQL tests. Its build cache and
   logs use CI-only locations; partial parsing is disabled.
6. `scripts/verify_dbt.py` reconciles row counts, anomalies, paid revenue and
   the daily/region marts. The CI contract requires exactly 5,000 rows,
   334 synthetic anomaly labels, 4,003,524.57 MAD paid revenue and zero
   aggregation mismatches.
7. The real Spark parity tests, isolated dbt integration test and static
   Airflow DAG tests run. The JSON validation report is uploaded as a workflow artifact.

**Status:** The commands were tested locally in V4.1–V4.3. The new GitHub
workflow itself must pass before V4.4.1 can be considered verified.

## Scope and safety

This gate neither starts Airflow nor builds the Airflow Docker image; those
remain separate operational checks. It does not change the V3 SQLite warehouse,
merge into `main`, or operate on customer data. All labels are synthetic.

## Optional local Windows reproduction

From the repository root with an installed `.venv` and Java 17:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_spark_windows.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_dbt_windows.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_tests_windows.ps1
docker compose --profile airflow config --quiet
```

If `data/raw/transactions.csv` is missing, regenerate it explicitly with
`.\.venv\Scripts\python.exe -m retailmind.generate --rows 5000 --seed 42`.
That optional command **overwrites the local raw synthetic CSV**; GitHub
Actions instead creates a fresh fixture on a disposable runner.
