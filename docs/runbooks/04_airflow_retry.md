# Airflow DAG failures, retries and dependencies

DAG: retailmind_data_ml_pipeline. Tasks: generate_transactions -> quality_gated_etl ->
build_warehouse -> train_and_evaluate. Inspect task attempt, exit code, scheduler logs,
upstream tasks, permissions and available disk before attributing a root cause.

Retries may recover transient errors but not missing required columns. The agent only
recommends checks; the operator decides whether to rerun a task.
