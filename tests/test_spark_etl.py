"""V4.1 Spark/pandas parity tests (real local Spark required)."""

import pandas as pd
import pytest

from retailmind.generate import generate
from retailmind.etl import run as pandas_etl


@pytest.mark.parametrize("rows", [200, 500])
def test_spark_matches_pandas_on_seeded_transactions(tmp_path, monkeypatch, rows):
    pytest.importorskip("pyspark")
    from retailmind import etl, spark_etl

    raw = tmp_path / "transactions.csv"
    pandas_csv = tmp_path / "transactions_clean.csv"
    spark_parquet = tmp_path / "spark_transactions.parquet"

    generate(rows=rows, seed=42, output=raw)
    monkeypatch.setattr(etl, "REPORTS", tmp_path)
    pandas_report = pandas_etl(raw, pandas_csv)
    spark_report = spark_etl.run(master="local[2]", source=raw, output=spark_parquet)

    pandas_frame = pd.read_csv(pandas_csv).sort_values("transaction_id").reset_index(drop=True)
    spark_frame = pd.read_parquet(spark_parquet).sort_values("transaction_id").reset_index(drop=True)

    assert spark_report["source_rows"] == pandas_report["source_rows"]
    assert spark_report["curated_rows"] == pandas_report["curated_rows"] == rows
    assert spark_report["duplicate_transaction_ids_in_source"] == pandas_report[
        "duplicate_transaction_ids_in_source"
    ]
    assert spark_report["rejected_rows_after_deduplication"] == 0
    assert spark_frame.transaction_id.is_unique
    assert spark_frame["transaction_id"].tolist() == pandas_frame["transaction_id"].tolist()
    for field in ("day", "event_timestamp", "region", "category", "payment_status", "anomaly_type"):
        assert spark_frame[field].tolist() == pandas_frame[field].tolist()
    for field in ("quantity", "unit_price", "discount_pct", "total_amount", "is_anomaly"):
        assert spark_frame[field].tolist() == pytest.approx(pandas_frame[field].tolist(), abs=1e-8)

    assert spark_report["injected_anomalies"] == int(pandas_frame["is_anomaly"].sum())
    assert spark_report["gross_order_value_mad"] == pytest.approx(
        round(float(pandas_frame["total_amount"].sum()), 2), abs=0.02
    )
    assert spark_report["paid_revenue_mad"] == pytest.approx(
        round(float(pandas_frame.loc[pandas_frame["payment_status"] == "paid", "total_amount"].sum()), 2),
        abs=0.02,
    )


def test_spark_rejects_missing_required_column(tmp_path):
    pytest.importorskip("pyspark")
    from retailmind import spark_etl

    source = tmp_path / "missing.csv"
    source.write_text("transaction_id,quantity\nTX-1,1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing required columns"):
        spark_etl.run(master="local[1]", source=source, output=tmp_path / "out.parquet")
