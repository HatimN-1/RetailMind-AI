"""Optional native PySpark ETL, outputs Parquet for distributed-processing demonstration."""
from __future__ import annotations
import json
from retailmind.settings import RAW, CURATED, ensure_dirs


def run(master: str = "local[*]") -> dict:
    try:
        from pyspark.sql import SparkSession, functions as F
    except ImportError as exc:
        raise RuntimeError("Install optional dependency: pip install -e '.[spark]'") from exc
    ensure_dirs()
    spark = (SparkSession.builder.master(master).appName("RetailMind-PySpark-ETL").getOrCreate())
    try:
        frame = spark.read.option("header", "true").option("inferSchema", "true").csv(str(RAW / "transactions.csv"))
        original = frame.count()
        frame = frame.dropDuplicates(["transaction_id"])
        frame = frame.withColumn("quantity", F.col("quantity").cast("int"))
        frame = frame.withColumn("discount_pct", F.col("discount_pct").cast("double"))
        frame = frame.withColumn("total_amount", F.col("total_amount").cast("double"))
        frame = frame.withColumn("is_anomaly", F.col("is_anomaly").cast("int"))
        frame = frame.filter((F.col("quantity") > 0) & (F.col("total_amount") >= 0) &
                             F.col("discount_pct").between(0, 1))
        frame = frame.withColumn("day", F.to_date(F.col("event_timestamp")))
        out = CURATED / "spark_transactions.parquet"
        frame.write.mode("overwrite").parquet(str(out))
        return {"source_rows": original, "spark_rows": frame.count(), "output": str(out), "master": master}
    finally:
        spark.stop()


def main():
    print(json.dumps(run(), indent=2))

if __name__ == "__main__":
    main()
