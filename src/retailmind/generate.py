"""Generate labeled synthetic e-commerce data. Never uses customer PII or real transactions."""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import random
import csv
from pathlib import Path
from retailmind.settings import RAW, ensure_dirs

REGIONS = ["Casablanca", "Rabat", "Fes", "Tanger", "Marrakech", "Agadir"]
PRODUCTS = [
    ("ELEC", "Electronics", 650.0), ("HOME", "Home", 230.0),
    ("FASH", "Fashion", 170.0), ("SPORT", "Sports", 320.0),
    ("BOOK", "Books", 85.0),
]
FIELDS = ["transaction_id", "event_timestamp", "customer_id", "product_id", "category", "region", "channel", "quantity", "unit_price", "discount_pct", "total_amount", "payment_status", "is_anomaly", "anomaly_type"]


def generate(rows: int = 5000, seed: int = 42, output: Path | None = None) -> dict:
    if rows < 50:
        raise ValueError("rows must be >= 50")
    ensure_dirs()
    rng = random.Random(seed)
    output = Path(output) if output else RAW / "transactions.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    anomalies = 0
    duplicates = 0
    records = []
    for i in range(rows):
        product_id, category, base_price = rng.choice(PRODUCTS)
        quantity = rng.randint(1, 4)
        unit_price = round(base_price * rng.uniform(0.77, 1.23), 2)
        discount = rng.choice([0.0, 0.0, 0.05, 0.1, 0.15])
        status = rng.choices(["paid", "failed", "pending"], [0.91, 0.05, 0.04])[0]
        kind = "normal"
        if rng.random() < 0.065:
            kind = rng.choice(["extreme_quantity", "extreme_price", "excessive_discount", "failed_high_value"])
            if kind == "extreme_quantity":
                quantity = rng.randint(18, 40)
            elif kind == "extreme_price":
                unit_price = round(base_price * rng.uniform(9, 17), 2)
            elif kind == "excessive_discount":
                discount = round(rng.uniform(0.75, 0.95), 2)
            elif kind == "failed_high_value":
                quantity = rng.randint(10, 22)
                status = "failed"
            anomalies += 1
        total = round(quantity * unit_price * (1.0 - discount), 2)
        event_time = start + timedelta(minutes=15 * i + rng.randint(0, 8))
        records.append({
            "transaction_id": f"TX-{i+1:07d}",
            "event_timestamp": event_time.isoformat(),
            "customer_id": f"C-{rng.randint(1, 1200):05d}",
            "product_id": product_id, "category": category,
            "region": rng.choice(REGIONS), "channel": rng.choice(["web", "mobile", "store"]),
            "quantity": quantity, "unit_price": unit_price, "discount_pct": discount,
            "total_amount": total, "payment_status": status,
            "is_anomaly": int(kind != "normal"), "anomaly_type": kind,
        })
    # Source-level duplicates are deliberately injected and removed by the ETL.
    extra = min(max(1, rows // 200), 100)
    for _ in range(extra):
        records.append(dict(rng.choice(records[:rows])))
        duplicates += 1
    rng.shuffle(records)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)
    return {"path": str(output), "seed": seed, "unique_transactions": rows,
            "source_rows": len(records), "injected_anomalies": anomalies,
            "injected_duplicates": duplicates, "synthetic": True}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate reproducible synthetic transactions")
    parser.add_argument("--rows", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    import json
    print(json.dumps(generate(args.rows, args.seed), indent=2))


if __name__ == "__main__":
    main()
