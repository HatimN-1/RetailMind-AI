export type MonitoringTask = {
  task_id: string; state: string | null; start_date: string | null;
  end_date: string | null; duration_seconds: number | null;
};
export type MonitoringRun = {
  run_id: string; state: string | null; execution_date: string | null;
  start_date: string | null; end_date: string | null;
  duration_seconds: number | null; tasks: MonitoringTask[];
};
export type MonitoringMetrics = {
  source: string; warehouse: string; transactions: number;
  injected_anomalies: number; paid_revenue_mad: number;
  daily_mismatches: number; region_mismatches: number; status: string;
};
export type MonitoringSnapshot = {
  schema_version: number; dag_id: string; captured_at: string;
  source: 'airflow_cli_snapshot'; live: false;
  runs: MonitoringRun[]; data_metrics: MonitoringMetrics | null;
};
