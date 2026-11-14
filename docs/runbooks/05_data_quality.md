# Data quality and analytical warehouse controls

Transaction IDs must be unique. quantity > 0, unit_price > 0, 0 <= discount_pct <= 1,
and total_amount >= 0. Confirm staging to mart row counts; compare grouped totals.

The dbt models test not_null and unique keys and aggregate daily and regional revenue.
Labels is_anomaly and anomaly_type are synthetic evaluation metadata and are prohibited
as model features. Use time-ordered holdout evaluation.
