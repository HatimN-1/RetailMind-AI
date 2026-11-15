"""Verify the dbt DuckDB marts against PySpark's Parquet source, read-only."""
from __future__ import annotations

import argparse
import json
from contextlib import chdir
from pathlib import Path


def verify(root: Path) -> dict:
    try:
        import duckdb
    except ImportError as exc:
        raise RuntimeError('Install analytics extras: pip install -e ".[analytics]"') from exc

    parquet = root / "data" / "curated" / "spark_transactions.parquet"
    database = root / "data" / "marts" / "retailmind.duckdb"
    if not database.is_file():
        raise FileNotFoundError(f"dbt database missing: {database}")
    if not parquet.is_dir() or not list(parquet.glob("*.parquet")):
        raise FileNotFoundError(f"PySpark Parquet missing: {parquet}")

    # dbt stored a relative read_parquet() path in the staging view.
    # Evaluate that view from dbt/, regardless of the CLI caller's working directory.
    with chdir(root / "dbt"), duckdb.connect(str(database), read_only=True) as con:
        source_count, source_anomalies, source_revenue = con.execute(
            """select count(*), sum(is_anomaly),
                      round(sum(case when payment_status = 'paid' then total_amount else 0 end), 2)
               from read_parquet(?)""",
            [str(parquet)],
        ).fetchone()
        stage_count, stage_unique, stage_anomalies, stage_revenue = con.execute(
            """select count(*), count(distinct transaction_id), sum(is_anomaly),
                      round(sum(case when payment_status = 'paid' then total_amount else 0 end), 2)
               from stg_transactions"""
        ).fetchone()
        daily_orders, daily_anomalies = con.execute(
            "select sum(orders), sum(injected_anomalies) from mart_daily_sales"
        ).fetchone()
        region_orders, region_anomalies = con.execute(
            "select sum(orders), sum(injected_anomalies) from mart_region_sales"
        ).fetchone()
        # Recalculate each mart's revenue from staging, comparing at its own aggregation grain.
        daily_mismatches = con.execute(
            """with expected as (
                   select transaction_day, count(*) as orders,
                          round(sum(case when payment_status='paid' then total_amount else 0 end), 2)
                          as revenue_mad,
                          sum(case when payment_status='failed' then 1 else 0 end) as failed_payments,
                          sum(is_anomaly) as injected_anomalies
                   from stg_transactions group by transaction_day
               )
               select count(*) from expected e full outer join mart_daily_sales m
                 on e.transaction_day = m.transaction_day
               where e.transaction_day is null or m.transaction_day is null
                  or e.orders <> m.orders
                  or abs(e.revenue_mad - m.revenue_mad) > 0.01
                  or e.failed_payments <> m.failed_payments
                  or e.injected_anomalies <> m.injected_anomalies"""
        ).fetchone()[0]
        region_mismatches = con.execute(
            """with expected as (
                   select region, count(*) as orders,
                          round(sum(case when payment_status='paid' then total_amount else 0 end), 2)
                          as revenue_mad,
                          sum(is_anomaly) as injected_anomalies
                   from stg_transactions group by region
               )
               select count(*) from expected e full outer join mart_region_sales m
                 on e.region = m.region
               where e.region is null or m.region is null
                  or e.orders <> m.orders
                  or abs(e.revenue_mad - m.revenue_mad) > 0.01
                  or e.injected_anomalies <> m.injected_anomalies"""
        ).fetchone()[0]

    assert source_count > 0, "Parquet source is empty"
    assert source_count == stage_count == stage_unique == daily_orders == region_orders, "Row-count mismatch"
    assert source_anomalies == stage_anomalies == daily_anomalies == region_anomalies, "Anomaly-count mismatch"
    assert abs(float(source_revenue) - float(stage_revenue)) <= 0.02, "Paid-revenue mismatch"
    assert daily_mismatches == region_mismatches == 0, "Mart aggregation mismatch"
    return {
        "source": "pyspark_parquet", "warehouse": "duckdb_dbt",
        "transactions": int(stage_count), "injected_anomalies": int(stage_anomalies),
        "paid_revenue_mad": float(stage_revenue), "daily_mismatches": int(daily_mismatches),
        "region_mismatches": int(region_mismatches), "status": "passed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Check dbt DuckDB against PySpark Parquet")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(json.dumps(verify(args.root.resolve()), indent=2))


if __name__ == "__main__":
    main()
