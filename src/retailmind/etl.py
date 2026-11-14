"""Quality-gated ETL; local pandas path with portable CSV output for dbt/SQLite."""
from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
from retailmind.settings import RAW, CURATED, REPORTS, ensure_dirs

REQUIRED = ["transaction_id", "event_timestamp", "quantity", "unit_price", "discount_pct", "total_amount", "payment_status", "is_anomaly", "anomaly_type", "region", "channel", "category"]


def run(source: Path | None = None, target: Path | None = None) -> dict:
    ensure_dirs()
    source = Path(source) if source else RAW / "transactions.csv"
    target = Path(target) if target else CURATED / "transactions_clean.csv"
    if not source.exists():
        raise FileNotFoundError(f"Missing {source}; first run python -m retailmind.generate")
    frame = pd.read_csv(source)
    missing = sorted(set(REQUIRED).difference(frame.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    count = len(frame)
    frame = frame.drop_duplicates(subset=["transaction_id"], keep="first").copy()
    numeric = ["quantity", "unit_price", "discount_pct", "total_amount", "is_anomaly"]
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["event_timestamp"] = pd.to_datetime(frame["event_timestamp"], utc=True, errors="coerce")
    frame = frame.dropna(subset=REQUIRED).copy()
    valid = (
        frame["quantity"].gt(0) & frame["unit_price"].gt(0) &
        frame["discount_pct"].between(0, 1) & frame["total_amount"].ge(0) &
        frame["is_anomaly"].isin([0, 1])
    )
    frame = frame.loc[valid].sort_values("event_timestamp").reset_index(drop=True)
    if frame.empty:
        raise ValueError("All rows filtered out; source invalid")
    frame["day"] = frame["event_timestamp"].dt.strftime("%Y-%m-%d")
    frame["event_timestamp"] = frame["event_timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, index=False)
    report = {"source_rows": count, "curated_rows": len(frame), "dropped_rows": count-len(frame),
              "duplicate_transaction_ids_in_source": int(count - len(pd.read_csv(source).drop_duplicates(subset=["transaction_id"]))),
              "positive_amounts": bool(frame["total_amount"].ge(0).all()),
              "unique_ids": bool(frame["transaction_id"].is_unique), "output": str(target),
              "note": "Injected labels are for offline evaluation, not production ground truth."}
    (REPORTS / "data_quality.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    print(json.dumps(run(), indent=2))


if __name__ == "__main__":
    main()
