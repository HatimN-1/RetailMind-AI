"""Optional PySpark ETL with pandas-equivalent checks for synthetic retail data.

The existing pandas CSV and SQLite warehouse remain untouched. The Spark
Parquet output is a separate V4 staging artifact for a future dbt integration.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from retailmind.etl import REQUIRED
from retailmind.settings import CURATED, RAW, ensure_dirs


def run(
    master: str = "local[2]",
    source: Path | None = None,
    output: Path | None = None,
) -> dict:
    """Clean the source with PySpark and write a standalone Parquet dataset.

    Duplicate IDs in the seeded generator always contain identical row values.
    As in pandas, duplicates are removed before row-level quality checks.
    The procedure does not mutate pandas outputs, the SQLite warehouse or ML artifacts.
    """
    try:
        from pyspark.sql import SparkSession, functions as F
    except ImportError as exc:
        raise RuntimeError(
            "PySpark is unavailable. Install with: "
            '.\\.venv\\Scripts\\python.exe -m pip install -e ".[spark]"'
        ) from exc

    ensure_dirs()
    source = Path(source) if source is not None else RAW / "transactions.csv"
    output = Path(output) if output is not None else CURATED / "spark_transactions.parquet"
    if not source.is_file():
        raise FileNotFoundError(f"Missing source CSV: {source}; run python -m retailmind.generate first")

    # Time zone is explicit so date partitions match the pandas UTC pipeline.
    spark = (
        SparkSession.builder.master(master)
        .appName("RetailMind-V4-PySpark-ETL")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    try:
        frame = spark.read.option("header", "true").option("inferSchema", "false").csv(str(source))
        missing = sorted(set(REQUIRED).difference(frame.columns))
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        source_rows = frame.count()
        unique = frame.dropDuplicates(["transaction_id"])
        deduplicated_rows = unique.count()

        # pandas.to_numeric(..., errors='coerce') followed by dropna and
        # the corresponding quality gates; retain the other original fields.
        for column in ("quantity", "unit_price", "discount_pct", "total_amount", "is_anomaly"):
            unique = unique.withColumn(column, F.col(column).cast("double"))
        unique = unique.withColumn("_parsed_timestamp", F.to_timestamp("event_timestamp"))

        clean = unique.dropna(subset=[*REQUIRED, "_parsed_timestamp"]).filter(
            (F.col("quantity") > 0)
            & (F.col("unit_price") > 0)
            & F.col("discount_pct").between(0.0, 1.0)
            & (F.col("total_amount") >= 0)
            & F.col("is_anomaly").isin(0.0, 1.0)
        )
        clean = (
            clean.withColumn("day", F.date_format("_parsed_timestamp", "yyyy-MM-dd"))
            .withColumn("event_timestamp", F.date_format("_parsed_timestamp", "yyyy-MM-dd'T'HH:mm:ss'Z'"))
            .withColumn("is_anomaly", F.col("is_anomaly").cast("int"))
            .drop("_parsed_timestamp")
        )

        # Reuse a single materialization for both metrics and the Parquet write.
        clean = clean.cache()
        try:
            curated_rows = clean.count()
            if curated_rows == 0:
                raise ValueError("All rows filtered out; source invalid")
            metrics = clean.agg(
                F.sum("total_amount").alias("gross_amount"),
                F.sum(F.when(F.col("payment_status") == "paid", F.col("total_amount")).otherwise(0.0))
                .alias("paid_revenue"),
                F.sum("is_anomaly").alias("injected_anomalies"),
            ).first()
            output.parent.mkdir(parents=True, exist_ok=True)
            clean.write.mode("overwrite").parquet(str(output))
        finally:
            clean.unpersist()

        return {
            "engine": "pyspark",
            "format": "parquet",
            "master": master,
            "source_rows": source_rows,
            "curated_rows": curated_rows,
            "duplicate_transaction_ids_in_source": source_rows - deduplicated_rows,
            "rejected_rows_after_deduplication": deduplicated_rows - curated_rows,
            "injected_anomalies": int(metrics["injected_anomalies"]),
            "gross_order_value_mad": round(float(metrics["gross_amount"]), 2),
            "paid_revenue_mad": round(float(metrics["paid_revenue"]), 2),
            "output": str(output),
            "note": "Synthetic labels are for offline evaluation only; no fraud claims.",
        }
    finally:
        spark.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="PySpark retail ETL -> standalone Parquet dataset")
    parser.add_argument("--master", default="local[2]", help="Spark master, e.g. local[2]")
    parser.add_argument("--source", type=Path, default=None, help="Optional input CSV")
    parser.add_argument("--output", type=Path, default=None, help="Optional Parquet directory")
    args = parser.parse_args()
    print(json.dumps(run(master=args.master, source=args.source, output=args.output), indent=2))


if __name__ == "__main__":
    main()
