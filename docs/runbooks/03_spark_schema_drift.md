# PySpark schema drift and ETL quality incidents

If the input CSV schema changes, check ingestion schema, failed casts, null ratios,
new enum values and incompatible timestamps. Run ETL checks before SQL mart updates.

Evidence sources: data/reports/data_quality.json and scheduler task logs.
Do not infer the specific failed column from a generic Spark exception unless an
actual log line identifies it. Stop downstream training when data-quality gates fail.
