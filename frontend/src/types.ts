export type PageId = 'overview' | 'transactions' | 'anomalies' | 'investigation' | 'quality' | 'monitoring';
export type Period = '7d' | '30d' | 'all';
export type SortKey = 'recent' | 'oldest' | 'amount_desc' | 'amount_asc';
export type Transaction = {
  transaction_id: string; day: string; region: string; category: string;
  channel: string; quantity: number; unit_price: number; discount_pct: number;
  total_amount: number; payment_status: string; is_anomaly: number;
  anomaly_type: string;
};
export type PageResult<T> = { items: T[]; total: number; limit: number; offset: number; has_more: boolean };
export type Analytics = {
  period: Period; latest_day: string | null; synthetic: boolean;
  summary: { orders: number; revenue_mad: number; gross_value_mad: number; anomalies: number; failed_payments: number };
  daily: Array<{ day: string; orders: number; revenue: number; anomalies: number }>;
  regions: Array<{ region: string; orders: number; revenue: number; anomalies: number }>;
  categories: Array<{ category: string; orders: number; revenue: number }>;
  payments: Array<{ status: string; orders: number }>;
  anomaly_types: Array<{ type: string; count: number }>;
};
export type QualityReport = {
  source_rows: number; curated_rows: number; dropped_rows: number;
  duplicate_transaction_ids_in_source: number; positive_amounts: boolean; unique_ids: boolean;
  output?: string; note?: string;
};
export type MLScore = { precision: number; recall: number; f1: number;
  average_precision: number; roc_auc: number; anomalies_predicted: number;
  epochs?: number; architecture?: string; note?: string;
};
export type ModelReport = {
  protocol: string; dataset: string; train_rows: number; test_rows: number;
  training_labels_used: boolean; test_labels_used_for_scoring_only: boolean;
  isolation_forest: MLScore; autoencoder_pytorch?: MLScore;
};
export type Investigation = {
  answer: string; mode: string; intent?: string;
  evidence?: Array<Record<string, unknown>>;
  sources?: Array<{ source: string; score?: number; text?: string; chunk_id?: string; backend?: string; start_line?: number; end_line?: number; quarantined?: boolean }>;
  question?: string; correlation_id?: string; latency_ms?: number;
  workflow_backend?: string; retrieval_backend?: string; synthesis_backend?: string;
  retrieval_diagnostics?: Array<{code: string; message: string; error_type: string; correlation_id?: string}>;
  ollama_attempted?: boolean; ollama_used?: boolean;
  observations?: Array<{text: string; references: string[]}>;
  hypotheses?: string[];
  recommendations?: Array<{text: string; references: string[]; source: string}>;
  sql_proofs?: Array<{id: string; tool: string; query: string; parameters: unknown[]; rows: Array<Record<string, unknown>>; row_count: number}>;
  steps?: Array<{node: string; status: string; latency_ms: number}>;
  warnings?: string[];
};

export type InvestigationStatus = {
  rag: {configured_backend: string; documents: number; chunks: number; qdrant_available: boolean; index_ready: boolean; status: string; embedding_model: string; diagnostic?: {code: string; message: string; error_type: string}};
  langgraph_available: boolean;
  ollama: {configured: boolean; available: boolean; status: string};
};
