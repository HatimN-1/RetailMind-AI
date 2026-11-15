import { useEffect, useState } from 'react';
import { Activity, CalendarClock, CheckCircle2, Clock3, Database, GitBranch, RefreshCw, ShieldCheck } from 'lucide-react';
import { api, integer } from '../api';
import { Metric, Panel, Pill, StatusNotice } from '../components/UI';
import { useLoad } from '../hooks';
import type { MonitoringRun, MonitoringTask } from '../monitoringTypes';
import './Monitoring.css';

const TASK_LABELS: Record<string, string> = {
  generate_synthetic_transactions: 'Génération synthétique',
  spark_etl_to_parquet: 'PySpark → Parquet',
  dbt_build_marts_and_tests: 'dbt → DuckDB',
  verify_dbt_vs_spark: 'Rapprochement des données',
};

const STATE_LABELS: Record<string, string> = {
  success: 'Réussi', failed: 'Échec', running: 'En cours', queued: 'En attente',
  scheduled: 'Planifié', upstream_failed: 'Bloqué', skipped: 'Ignoré',
};

const stateVariant = (state: string | null): 'good' | 'bad' | 'warn' | 'purple' | 'neutral' =>
  state === 'success' ? 'good' : ['failed', 'upstream_failed'].includes(state || '') ? 'bad'
  : state === 'running' ? 'purple' : ['queued', 'scheduled'].includes(state || '') ? 'warn' : 'neutral';

const stamp = (value: string | null | undefined): string => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('fr-MA', {
    timeZone: 'Africa/Casablanca', dateStyle: 'short', timeStyle: 'medium',
  });
};

const elapsed = (value: number | null): string => value === null ? '—'
  : value >= 60 ? `${Math.floor(value / 60)} min ${Math.round(value % 60)} s` : `${value.toFixed(1)} s`;

type RunFilter = 'all' | 'success' | 'failed' | 'active';
const FILTERS: Array<{id: RunFilter; label: string}> = [
  {id: 'all', label: 'Tous'}, {id: 'success', label: 'Réussis'},
  {id: 'failed', label: 'Échecs'}, {id: 'active', label: 'En cours'},
];
const matchesFilter = (state: string | null, filter: RunFilter): boolean =>
  filter === 'all' || (filter === 'success' && state === 'success') ||
  (filter === 'failed' && ['failed', 'upstream_failed'].includes(state || '')) ||
  (filter === 'active' && ['running', 'queued', 'scheduled'].includes(state || ''));

function TaskRow({ task, maximum }: {task: MonitoringTask; maximum: number}) {
  const width = task.duration_seconds === null ? 0
    : Math.max(3, Math.min(100, task.duration_seconds / maximum * 100));
  return <div className="v45-task">
    <div className="v45-task-top"><div><b>{TASK_LABELS[task.task_id] || task.task_id}</b><small>{stamp(task.start_date)}</small></div>
      <Pill variant={stateVariant(task.state)}>{STATE_LABELS[task.state || ''] || task.state || 'Inconnu'}</Pill>
    </div>
    <div className="v45-duration"><div className="v45-track"><span style={{width: `${width}%`}} /></div>
      <strong>{elapsed(task.duration_seconds)}</strong></div>
  </div>;
}

export default function Monitoring() {
  const monitor = useLoad(() => api.monitoring(), []);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [filter, setFilter] = useState<RunFilter>('all');
  const [now, setNow] = useState(() => Date.now());
  // Poll the read-only FastAPI JSON file, NOT the Airflow API or Docker.
  useEffect(() => {
    const timer = window.setInterval(() => { setNow(Date.now()); monitor.reload(); }, 60_000);
    return () => window.clearInterval(timer);
  }, [monitor.reload]);
  if (monitor.loading && !monitor.data) return <StatusNotice message="Lecture du dernier instantané Airflow..." />;
  if (monitor.error || !monitor.data) return <>
    <div className="page-title-row"><div><div className="eyebrow">DATA ENGINEERING / OBSERVABILITY</div>
      <h1>Monitoring des pipelines</h1><p className="page-subtitle">Historique Airflow et qualité dbt, depuis un instantané en lecture seule.</p></div></div>
    <StatusNotice kind="error" message={monitor.error || 'Aucun instantané disponible'} retry={monitor.reload}/>
    <p className="v45-guidance">Pour alimenter cette page, exécuter localement : <code>python scripts/export_v4_monitoring.py</code>, puis cliquer sur « Réessayer ».</p>
  </>;
  const snapshot = monitor.data;
  const filteredRuns = snapshot.runs.filter(item => matchesFilter(item.state, filter));
  const run: MonitoringRun | undefined = filteredRuns.find(item => item.run_id === selectedRun) || filteredRuns[0];
  const tasks = run?.tasks || [];
  const successes = tasks.filter(task => task.state === 'success').length;
  const maxTask = Math.max(1, ...tasks.map(task => task.duration_seconds || 0));
  const metrics = snapshot.data_metrics;
  const snapshotAge = now - new Date(snapshot.captured_at).getTime();
  const old = Number.isFinite(snapshotAge) && snapshotAge > 60 * 60 * 1000;

  return <>
    <div className="page-title-row"><div><div className="eyebrow">DATA ENGINEERING / OBSERVABILITY</div>
      <h1>Monitoring des pipelines</h1>
      <p className="page-subtitle">Exécutions réelles du DAG Airflow et rapprochement PySpark, dbt et DuckDB.</p></div>
      <button type="button" className="btn btn-outline" onClick={() => { setNow(Date.now()); monitor.reload(); }}
        disabled={monitor.loading}><RefreshCw size={15}/> {monitor.loading ? 'Lecture...' : "Relire l'instantané"}</button>
    </div>
    <div className={`v45-snapshot ${old ? 'v45-snapshot-old' : ''}`}>
      <CalendarClock size={18}/><div><b>Instantané local · non temps réel</b>
        <span>Capture : {stamp(snapshot.captured_at)} (heure de Casablanca){old ? ' · Plus d’une heure' : ''}.</span></div>
      <span>Relecture du JSON toutes les 60 s. Pour actualiser Airflow, relancer l'export PowerShell.</span>
    </div>
    <div className="metric-grid four">
      <Metric label="Exécution affichée" value={run ? STATE_LABELS[run.state || ''] || run.state || 'Inconnue' : 'Aucune'}
        hint={run ? stamp(run.end_date) : 'Aucun run dans le snapshot'} icon={<GitBranch size={19}/>} accent="violet"/>
      <Metric label="Tâches réussies" value={`${successes} / ${tasks.length}`} hint="Sur l'exécution sélectionnée"
        icon={<CheckCircle2 size={19}/>} accent="teal"/>
      <Metric label="Durée du DAG" value={run ? elapsed(run.duration_seconds) : '—'}
        hint="Entre début et fin Airflow" icon={<Clock3 size={19}/>} accent="amber"/>
      <Metric label="Qualité des données" value={metrics?.status === 'passed' ? 'Validée' : 'Non mesurée'}
        hint="Rapprochement Parquet / DuckDB" icon={<ShieldCheck size={19}/>} accent="pink"/>
    </div>
    <div className="v45-layout">
      <Panel title="Historique des exécutions" subtitle={`${snapshot.runs.length} exécution(s) exportée(s) · jusqu'à 20`}>
        <div className="v45-filters" role="group" aria-label="Filtrer les exécutions">
          {FILTERS.map(option => <button type="button" key={option.id}
            aria-pressed={filter === option.id} className={filter === option.id ? 'selected' : ''}
            onClick={() => setFilter(option.id)}>{option.label} <span>
              {snapshot.runs.filter(item => matchesFilter(item.state, option.id)).length}</span></button>)}
        </div>
        <div className="v45-run-list">{filteredRuns.map(item => <button key={item.run_id} type="button"
          className={`v45-run ${run?.run_id === item.run_id ? 'selected' : ''}`} onClick={() => setSelectedRun(item.run_id)}>
          <div><b>{stamp(item.execution_date)}</b><small title={item.run_id}>{item.run_id}</small></div>
          <div><Pill variant={stateVariant(item.state)}>{STATE_LABELS[item.state || ''] || item.state || 'Inconnu'}</Pill>
            <small>{elapsed(item.duration_seconds)}</small></div>
        </button>)}{filteredRuns.length === 0 && <p className="v45-empty">Aucune exécution pour ce filtre.</p>}</div>
      </Panel>
      <Panel title="Étapes du pipeline" subtitle={run ? `Run : ${run.run_id}` : 'Aucun run sélectionné'}>
        <div className="v45-task-list">{tasks.map(task => <TaskRow key={task.task_id} task={task} maximum={maxTask}/>)}
          {!tasks.length && <p className="v45-empty">Aucune tâche dans cette exécution.</p>}</div>
        <div className="v45-foot"><Activity size={15}/> Durées mesurées par Airflow, calculées entre début et fin de chaque tâche.</div>
      </Panel>
    </div>
    <Panel title="Contrat de données V4" subtitle="État de l'entrepôt au moment de la capture (non lié au run sélectionné) · données synthétiques"
      action={<Pill variant={metrics?.status === 'passed' ? 'good' : 'neutral'}>{metrics?.status === 'passed' ? 'Rapprochement OK' : 'Non vérifié'}</Pill>}>
      {metrics ? <div className="v45-data-grid">
        <div><Database size={17}/><span>Transactions</span><strong>{integer(metrics.transactions)}</strong></div>
        <div><Activity size={17}/><span>Anomalies injectées</span><strong>{integer(metrics.injected_anomalies)}</strong></div>
        <div><ShieldCheck size={17}/><span>Revenu payé</span><strong>{new Intl.NumberFormat('fr-MA', {minimumFractionDigits: 2, maximumFractionDigits: 2}).format(metrics.paid_revenue_mad)} MAD</strong></div>
        <div><CheckCircle2 size={17}/><span>Écarts quotidiens / régionaux</span>
          <strong>{metrics.daily_mismatches} / {metrics.region_mismatches}</strong></div>
      </div> : <p className="v45-empty">Relancer l'export sans l'option <code>--skip-data</code> pour afficher les métriques.</p>}
    </Panel>
  </>;
}
