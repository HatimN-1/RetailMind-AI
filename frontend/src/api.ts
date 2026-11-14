import type { Analytics, Investigation, InvestigationStatus, ModelReport, PageResult, Period, QualityReport, Transaction } from './types';

const BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message: string, public code: number, public correlationId?: string, public errorType?: string) {
    super(message + (correlationId ? ` Référence : ${correlationId}.` : ''));
    this.name = 'ApiError';
  }
}

const record = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

function detailMessage(detail: unknown): string | undefined {
  if (typeof detail === 'string') return detail;
  if (record(detail) && typeof detail.message === 'string') return detail.message;
  if (Array.isArray(detail)) return detail.filter(record).map(item => {
    const field = Array.isArray(item.loc) ? item.loc.filter(part => part !== 'body').join('.') : '';
    return `${field ? field + ' : ' : ''}${typeof item.msg === 'string' ? item.msg : 'Valeur invalide'}`;
  }).join(' ; ') || undefined;
  return undefined;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), path === '/investigate' ? 70000 : 10000);
  try {
    const response = await fetch(BASE + path, { ...init, signal: init?.signal || controller.signal,
      headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) } });
    let body: unknown;
    try {
      body = await response.json();
    } catch (error) {
      if (controller.signal.aborted) throw error;
      throw new ApiError(response.ok ? 'Réponse inattendue du backend : JSON attendu. Vérifier FastAPI et le proxy /api.'
        : `Erreur du backend (HTTP ${response.status}). Consulter les journaux FastAPI.`, response.status,
        response.headers.get('X-Correlation-ID') || undefined);
    }
    if (!response.ok) {
      const data = record(body) ? body : {};
      const correlation = typeof data.correlation_id === 'string' ? data.correlation_id
        : response.headers.get('X-Correlation-ID') || undefined;
      const errorType = typeof data.error_type === 'string' ? data.error_type : undefined;
      const message = detailMessage(data.detail) || `Erreur du backend (HTTP ${response.status})`;
      throw new ApiError(message + (errorType ? ` (${errorType})` : ''), response.status, correlation, errorType);
    }
    return body as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (controller.signal.aborted || (error instanceof Error && ['AbortError', 'TimeoutError'].includes(error.name))) {
      throw new ApiError('Délai de réponse dépassé. Vérifier les services locaux puis réessayer la question.', 0);
    }
    throw new ApiError('Impossible de joindre FastAPI. Vérifier le backend sur le port 8000 et le proxy /api.', 0);
  } finally {
    clearTimeout(timer);
  }
}

function investigationResponse(value: unknown): Investigation {
  const list = (items: unknown, valid: (item: unknown) => boolean) => items === undefined ||
    (Array.isArray(items) && items.every(valid));
  const strings = (items: unknown) => Array.isArray(items) && items.every(item => typeof item === 'string');
  const cited = (item: unknown) => record(item) && typeof item.text === 'string' && strings(item.references);
  const finite = (item: unknown) => typeof item === 'number' && Number.isFinite(item);
  if (!record(value) || typeof value.answer !== 'string' || typeof value.mode !== 'string' ||
      (value.latency_ms !== undefined && !finite(value.latency_ms)) ||
      !list(value.evidence, record) || !list(value.warnings, item => typeof item === 'string') ||
      !list(value.hypotheses, item => typeof item === 'string') || !list(value.observations, cited) ||
      !list(value.recommendations, item => cited(item) && record(item) && typeof item.source === 'string') ||
      !list(value.sources, item => record(item) && typeof item.source === 'string' &&
        (item.score === undefined || finite(item.score)) && (item.text === undefined || typeof item.text === 'string')) ||
      !list(value.steps, item => record(item) && typeof item.node === 'string' &&
        typeof item.status === 'string' && finite(item.latency_ms)) ||
      !list(value.sql_proofs, item => record(item) && ['id', 'tool', 'query'].every(k => typeof item[k] === 'string') &&
        Array.isArray(item.parameters) && Array.isArray(item.rows) && item.rows.every(record) && finite(item.row_count))) {
    throw new ApiError('Réponse d’investigation incompatible avec l’interface. Redémarrer FastAPI avec le backend V3.', 200);
  }
  return value as Investigation;
}
export const api = {
  health: () => request<{ service: string; warehouse_ready: boolean; data_type: string }>('/health'),
  analytics: (period: Period) => request<Analytics>(`/analytics?period=${period}`),
  transactions: (query: URLSearchParams) => request<PageResult<Transaction>>(`/transactions-page?${query}`),
  alerts: (query: URLSearchParams) => request<PageResult<Transaction>>(`/alerts-page?${query}`),
  quality: () => request<QualityReport>('/quality'),
  evaluation: () => request<ModelReport>('/model-evaluation'),
  investigationStatus: () => request<InvestigationStatus>('/investigation-status'),
  runbook: (source: string) => request<{source: string; title: string; text: string}>(`/rag/documents/${source.replace(/^docs\/runbooks\//, '').split('/').map(encodeURIComponent).join('/')}`),
  investigate: async (question: string, useLangGraph: boolean) => investigationResponse(await request<unknown>('/investigate', {
    method: 'POST', body: JSON.stringify({ question, use_langgraph: useLangGraph })
  }))
};

export const money = (n: number | null | undefined) =>
  new Intl.NumberFormat('fr-MA', { maximumFractionDigits: 0 }).format(n || 0) + ' MAD';
export const integer = (n: number | null | undefined) => new Intl.NumberFormat('fr-MA').format(n || 0);
export const percent = (n: number | null | undefined) => `${((n || 0) * 100).toFixed(1).replace('.', ',')} %`;
export const shortDay = (d: string) => { const parts = d.split('-'); return parts.length === 3 ? `${parts[2]}/${parts[1]}` : d; };

export function exportCsv(rows: Array<Record<string, unknown>>, name: string) {
  if (!rows.length) return;
  const columns = Object.keys(rows[0]);
  const escape = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const content = '\uFEFF' + columns.join(';') + '\r\n' + rows.map(r => columns.map(c => escape(r[c])).join(';')).join('\r\n');
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = name; a.click();
  URL.revokeObjectURL(url);
}
