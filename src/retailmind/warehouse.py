"""Portable SQL analytical mart: usable even when DuckDB/dbt are not installed."""
from __future__ import annotations
import json
import sqlite3
import pandas as pd
from retailmind.settings import CURATED, DB, MARTS, ensure_dirs


def build() -> dict:
    ensure_dirs()
    path = CURATED / "transactions_clean.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}; run ETL first")
    frame = pd.read_csv(path)
    with sqlite3.connect(DB) as conn:
        frame.to_sql("transactions", conn, if_exists="replace", index=False)
        conn.executescript("""
          CREATE INDEX IF NOT EXISTS ix_tx_id ON transactions(transaction_id);
          DROP TABLE IF EXISTS daily_metrics;
          CREATE TABLE daily_metrics AS
          SELECT day, COUNT(*) AS orders, ROUND(SUM(CASE WHEN payment_status='paid' THEN total_amount ELSE 0 END),2) AS revenue,
                 SUM(CASE WHEN payment_status='failed' THEN 1 ELSE 0 END) AS failed_payments,
                 SUM(is_anomaly) AS injected_anomalies
          FROM transactions GROUP BY day ORDER BY day;
          DROP TABLE IF EXISTS region_metrics;
          CREATE TABLE region_metrics AS
          SELECT region, COUNT(*) AS orders, ROUND(SUM(CASE WHEN payment_status='paid' THEN total_amount ELSE 0 END),2) AS revenue,
                 SUM(is_anomaly) AS injected_anomalies
          FROM transactions GROUP BY region ORDER BY revenue DESC;
        """)
        summary = conn.execute("SELECT COUNT(*), ROUND(SUM(total_amount),2), ROUND(SUM(CASE WHEN payment_status='paid' THEN total_amount ELSE 0 END),2), SUM(is_anomaly) FROM transactions").fetchone()
    report = {"transactions": summary[0], "gross_order_value_mad": summary[1], "paid_revenue_mad": summary[2],
              "injected_anomalies": summary[3], "database": str(DB)}
    (MARTS / "warehouse_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def execute_readonly(query: str, params: tuple = ()) -> list[dict]:
    """Internal-only SELECT API. Never expose arbitrary user SQL."""
    normalized = query.strip().lower()
    if not normalized.startswith("select ") or ";" in query:
        raise ValueError("Only a single SELECT query is permitted")
    if not DB.exists():
        return []
    with sqlite3.connect(DB.resolve().as_uri() + "?mode=ro", uri=True, timeout=3) as conn:
        conn.execute("PRAGMA query_only = ON")
        # Bounded execution even if a future internal analytical query is expensive.
        import time
        deadline = time.monotonic() + 3
        conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def main():
    print(json.dumps(build(), indent=2))


if __name__ == "__main__":
    main()
