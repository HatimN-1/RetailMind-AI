# RetailMind V4.2 - dbt + DuckDB over PySpark Parquet

The V4.1 Spark ETL writes a directory at `data/curated/spark_transactions.parquet/` containing
`part-*.parquet`. The V4.2 staging model now reads these Parquet parts directly. It does not
replace the V3 pandas CSV or SQLite database; existing FastAPI, React, ML and RAG remain unchanged.

## Windows (PowerShell, repository root)

```powershell
# 1. Install the optional adapter and DuckDB in the existing .venv
.\.venv\Scripts\python.exe -m pip install -e ".[analytics]"

# 2. Ensure the Parquet data exists (rerun if necessary)
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_spark_windows.ps1

# 3. Build dbt staging + marts, run all tests and verify sums against Parquet
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_dbt_windows.ps1

# 4. Integration test with a synthetic fixture isolated under pytest's tmp_path
.\.venv\Scripts\python.exe -m pytest tests/test_dbt_pipeline.py -v
```

The wrapper runs from `dbt/` because the existing DuckDB profile and the new staging
model use paths relative to that working directory. The resulting database is
`data/marts/retailmind.duckdb` and is ignored by Git. `dbt/target` and `dbt/logs` are ignored too.

## Expected checks

- Staging has one unique transaction per ID; data types are set explicitly.
- dbt `build` materializes `mart_daily_sales` and `mart_region_sales` and runs standard
  uniqueness/not-null tests plus a custom transaction-quality test.
- `scripts/verify_dbt.py` compares row counts, anomaly totals, paid revenue, and
  daily/region aggregates with the PySpark Parquet data.
- With the seed-42 5,000-transaction dataset, the expected source counts are 5,000
  unique transactions and 334 synthetic anomaly labels; paid revenue is 4,003,524.57 MAD.
  These numbers must be reproduced locally and are not evidence of real-world fraud.

## Scope

This is an optional, additive warehouse path; the existing SQLite warehouse remains
V3's API source. Do not point the live API at DuckDB until its contracts and integration
tests are updated in a later, separate change. The next milestone is Airflow orchestration.
