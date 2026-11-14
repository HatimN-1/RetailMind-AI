import { Activity, ArrowUpRight, CheckCircle2, Database, Gauge, GitBranch, ScanSearch, ShieldCheck } from 'lucide-react';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { api, integer, percent } from '../api';
import { useLoad } from '../hooks';
import { Metric, Panel, Pill, StatusNotice } from '../components/UI';

const tooltipStyle={border:'1px solid #304061',backgroundColor:'#12223b',borderRadius:12,color:'#eaf0fc',fontSize:12};
export default function Quality() {
  const quality=useLoad(()=>api.quality(),[]);
  const report=useLoad(()=>api.evaluation(),[]);
  if((quality.loading&&!quality.data)||(report.loading&&!report.data))return <StatusNotice message="Lecture des rapports de qualité et ML..."/>;
  if(quality.error||report.error) return <StatusNotice kind="error" message={quality.error||report.error||'Erreur'} retry={()=>{quality.reload();report.reload();}}/>;
  if(!quality.data||!report.data)return null;
  const q=quality.data, r=report.data;
  const comparison=[{name:'Precision',isolation:r.isolation_forest.precision,pytorch:r.autoencoder_pytorch?.precision},{name:'Recall',isolation:r.isolation_forest.recall,pytorch:r.autoencoder_pytorch?.recall},{name:'F1',isolation:r.isolation_forest.f1,pytorch:r.autoencoder_pytorch?.f1},{name:'PR-AUC',isolation:r.isolation_forest.average_precision,pytorch:r.autoencoder_pytorch?.average_precision}];
  const success=q.positive_amounts&&q.unique_ids;
  return <>
    <div className="page-title-row"><div><div className="eyebrow">DATA PLATFORM / OBSERVABILITY</div><h1>Qualité & Machine Learning</h1><p className="page-subtitle">Contrôles d'intégration, reproductibilité et comparaison des modèles sur le jeu synthétique.</p></div><div className="header-pill"><ShieldCheck size={16}/> Protocole documenté</div></div>
    <div className="metric-grid three"><Metric label="Lignes sources" value={integer(q.source_rows)} hint="Avant suppression des doublons" icon={<Database size={19}/>} accent="violet"/><Metric label="Lignes conservées" value={integer(q.curated_rows)} hint="Jeu nettoyé disponible dans SQLite" icon={<CheckCircle2 size={19}/>} accent="teal"/><Metric label="Doublons supprimés" value={integer(q.dropped_rows)} hint="IDs de transaction répétés" icon={<ScanSearch size={19}/>} accent="amber"/></div>
    <div className="charts-grid">
      <Panel title="Contrôles du pipeline" subtitle="Vérifications déterministes réalisées après nettoyage" action={<Pill variant={success?'good':'bad'}>{success?'Contrôles OK':'Anomalie qualité'}</Pill>}>
        <div className="quality-stack"><div><div className="quality-check"><CheckCircle2 size={19}/><b>Identifiants uniques</b><Pill variant={q.unique_ids?'good':'bad'}>{q.unique_ids?'Validé':'Échec'}</Pill></div><p>Absence de doublons dans le jeu consolidé.</p></div><div><div className="quality-check"><CheckCircle2 size={19}/><b>Montants positifs</b><Pill variant={q.positive_amounts?'good':'bad'}>{q.positive_amounts?'Validé':'Échec'}</Pill></div><p>Contrôle de cohérence des montants.</p></div><div><div className="quality-check"><GitBranch size={19}/><b>Déduplication</b><Pill variant="purple">{integer(q.duplicate_transaction_ids_in_source)} supprimés</Pill></div><p>Les doublons sont injectés intentionnellement lors de la génération.</p></div></div>
        <div className="quality-meter"><div className="quality-meter-label"><span>Conservation des lignes</span><strong>{(q.source_rows?100*q.curated_rows/q.source_rows:0).toFixed(2)} %</strong></div><div className="progress-track"><div style={{width:`${q.source_rows?100*q.curated_rows/q.source_rows:0}%`}}/></div></div>
      </Panel>
      <Panel title="Performance des modèles" subtitle="Holdout temporel : entraînement 75 % / test 25 %" action={<Pill variant="purple">Sans labels en training</Pill>}>
        <div className="chart-holder quality-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={comparison} margin={{top:14,left:-20,right:8,bottom:5}}><CartesianGrid vertical={false} stroke="#263850" strokeDasharray="4 5"/><XAxis dataKey="name" tick={{fill:'#8192ad',fontSize:12}} axisLine={false} tickLine={false}/><YAxis domain={[0,1]} tickFormatter={v=>`${Math.round(v*100)}%`} tick={{fill:'#8192ad',fontSize:11}} axisLine={false} tickLine={false}/><Tooltip contentStyle={tooltipStyle} formatter={v=>percent(Number(v))}/><Legend wrapperStyle={{fontSize:11}}/><Bar dataKey="isolation" name="Isolation Forest" fill="#9f83f7" radius={[6,6,0,0]} maxBarSize={32}/>{r.autoencoder_pytorch&&<Bar dataKey="pytorch" name="Autoencodeur PyTorch" fill="#27d3b5" radius={[6,6,0,0]} maxBarSize={32}/>}</BarChart></ResponsiveContainer></div>
        {!r.autoencoder_pytorch&&<p className="small-footnote">Autoencodeur optionnel non évalué dans ce rapport. Installer le module deep puis relancer l'entraînement.</p>}
      </Panel>
    </div>
    <div className="metric-grid two"><Metric label="F1 Isolation Forest" value={percent(r.isolation_forest.f1)} hint={`Rappel : ${percent(r.isolation_forest.recall)}`} icon={<Gauge size={19}/>} accent="violet"/><Metric label="F1 Autoencodeur PyTorch" value={r.autoencoder_pytorch?percent(r.autoencoder_pytorch.f1):'Non mesuré'} hint={r.autoencoder_pytorch?`Rappel : ${percent(r.autoencoder_pytorch.recall)}`:'Module Deep Learning optionnel'} icon={<Activity size={19}/>} accent="teal"/></div>
    <Panel title="Méthodologie et limites" subtitle="À utiliser pour l'explication technique en entretien"><div className="method-grid"><div><span className="method-tag">01</span><h4>Génération</h4><p>Transactions totalement artificielles avec anomalies et doublons injectés de manière reproductible.</p></div><div><span className="method-tag">02</span><h4>Protocole temporel</h4><p>{integer(r.train_rows)} lignes d'apprentissage, {integer(r.test_rows)} lignes de test, sans utilisation des labels en apprentissage.</p></div><div><span className="method-tag">03</span><h4>Interprétation</h4><p>Les scores caractérisent la détection d'anomalies simulées, pas une efficacité anti-fraude en production.</p></div></div><div className="foot-tag"><ArrowUpRight size={17}/> Référence : {r.protocol} · {r.dataset}</div></Panel>
  </>;
}
