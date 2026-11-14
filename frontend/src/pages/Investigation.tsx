import { useEffect, useRef, useState } from 'react';
import { ArrowUpRight, BookOpen, Bot, BrainCircuit, CheckCircle2, CornerDownLeft, FileSearch, LockKeyhole, MessageSquareText, Send, Sparkles, User2 } from 'lucide-react';
import { api } from '../api';
import type { Investigation, InvestigationStatus } from '../types';
import { Panel, Pill } from '../components/UI';

type Message={id:number;role:'user'|'assistant';content:string;result?:Investigation;error?:boolean;retryQuestion?:string};
const SUGGESTIONS=[
  'Quelles transactions présentent des anomalies ?',
  'Que vérifier après un échec du pipeline Airflow ?',
  'Quelles régions génèrent le plus de revenus ?',
  'Analyse la transaction TX-0003699',
  'Comment diagnostiquer une erreur de schéma Spark ?',
  'Quelles vérifications effectuer après un test dbt échoué ?'
];
const NODE_NAMES:Record<string,string>={validation:'Validation',classification:'Intention',routing:'Parcours',sql_evidence:'Preuves SQL',document_retrieval:'Recherche documentaire',factual_context:'Contexte factuel',synthesis:'Synthèse',verification:'Vérification',final_report:'Rapport final'};
function Report({result}:{result:Investigation}) {
  if(result.intent==='refused'||result.intent==='unsupported'||!result.observations) return <>{result.answer}</>;
  return <div className="investigation-report">
    <h4>FAITS OBSERVÉS</h4>
    {result.observations.length?result.observations.map((o,i)=><p key={i}>{o.text} <small>[{o.references.join(', ')}]</small></p>):<p>Aucune preuve SQL ou aucun journal d’exécution disponible. Aucune cause d’incident confirmée.</p>}
    {result.sql_proofs?.[0]?.parameters.length!==0&&result.intent==='transaction'&&<p>Identifiant recherché : {String(result.sql_proofs?.[0]?.parameters[0])}</p>}
    <h4>HYPOTHÈSES</h4>{result.hypotheses?.map((h,i)=><p key={i}>{h}</p>)}
    <h4>VÉRIFICATIONS RECOMMANDÉES</h4>
    {result.recommendations?.length?result.recommendations.map((r,i)=><details key={i} open={i===0}><summary>{r.source.split('/').pop()}</summary><p>{r.text}</p><small>Extrait documentaire général · {r.references.join(', ')}</small></details>):<p>Aucun extrait pertinent disponible ; revue humaine nécessaire.</p>}
    <h4>SOURCES</h4>{result.sources?.map((s,i)=><p key={i}>{s.source.split('/').pop()} · {s.backend} · score {s.score?.toFixed(3)}{s.quarantined?' · exclue de la synthèse':''}</p>)}
    <div className="report-limits">{result.warnings?.map((w,i)=><p key={i}>{w}</p>)}</div>
  </div>;
}
export default function InvestigationPage() {
  const [question,setQuestion]=useState('');
  const [useGraph,setUseGraph]=useState(true);
  const [loading,setLoading]=useState(false);
  const [messages,setMessages]=useState<Message[]>([{id:0,role:'assistant',content:'Bonjour ! Je consulte exclusivement les données SQL synthétiques et les runbooks locaux. Chaque conclusion conserve ses preuves et son mode réel d’exécution.'}]);
  const [selected,setSelected]=useState<Investigation|null>(null);
  const [status,setStatus]=useState<InvestigationStatus|null>(null);
  const [statusError,setStatusError]=useState('');
  const [document,setDocument]=useState<{source:string;text:string}|null>(null);
  const [documentError,setDocumentError]=useState('');
  const [documentLoading,setDocumentLoading]=useState(false);
  const bottom=useRef<HTMLDivElement>(null);
  const sending=useRef(false);
  async function refreshStatus(){try{setStatus(await api.investigationStatus());setStatusError('');}catch(e){setStatus(null);setStatusError(e instanceof Error?e.message:'Statut indisponible');}}
  useEffect(()=>{void refreshStatus();},[]);
  useEffect(()=>{
    // Some browsers return a Promise from scrolling; effects must return only cleanup functions.
    bottom.current?.scrollIntoView({behavior:'smooth',block:'nearest'});
  },[messages,loading]);
  async function openDocument(source:string){setDocumentLoading(true);setDocumentError('');setDocument(null);try{setDocument(await api.runbook(source));}catch(e){setDocumentError(e instanceof Error?e.message:'Runbook indisponible');}finally{setDocumentLoading(false);}}
  async function send(text=question) {
    const value=text.trim(); if(!value||sending.current) return;
    sending.current=true;
    setQuestion('');setLoading(true);
    setMessages(old=>[...old,{id:Date.now(),role:'user',content:value}]);
    try {const result=await api.investigate(value,useGraph);setMessages(old=>[...old,{id:Date.now()+1,role:'assistant',content:result.answer,result}]);setSelected(result);}
    catch(e){setMessages(old=>[...old,{id:Date.now()+1,role:'assistant',content:e instanceof Error?e.message:'Erreur inconnue',error:true,retryQuestion:value}]);}
    finally{sending.current=false;setLoading(false);void refreshStatus();}
  }
  return <>
    <div className="page-title-row"><div><div className="eyebrow">AGENTIC AI / GOVERNED INVESTIGATION</div><h1>Investigation IA <span className="heading-spark">✦</span></h1><p className="page-subtitle">Explore les signaux synthétiques et les runbooks avec des preuves traçables.</p></div><div className="header-pill"><LockKeyhole size={16}/> Agent en lecture seule</div></div>
    <div className="investigation-layout">
      <div className="conversation panel"><div className="conversation-top"><div className="agent-avatar"><Bot size={22}/></div><div><h3>RetailMind Investigator</h3><p>SQL autorisé · sources locales · V3</p></div><Pill variant="purple">Local</Pill></div>
        <div className="messages" aria-live="polite" aria-busy={loading}>
          {messages.map(m=><div key={m.id} className={`message ${m.role}`}><div className="message-icon">{m.role==='assistant'?<Bot size={18}/>:<User2 size={18}/>}</div><div className="message-body"><small>{m.role==='assistant'?'RETAILMIND AI':'VOUS'}</small><div role={m.error?'alert':undefined} className={`bubble ${m.error?'error':''}`}>{m.result?<Report result={m.result}/>:m.content}</div>{m.error&&m.retryQuestion&&<button className="evidence-link" disabled={loading} onClick={()=>void send(m.retryQuestion!)}>Réessayer cette question</button>}{m.result&&<><div className="report-meta"><BrainCircuit size={14}/>{m.result.mode} · {m.result.latency_ms?.toFixed(0)} ms</div><button className="evidence-link" onClick={()=>{setSelected(m.result!);setDocument(null);}}><FileSearch size={14}/> Voir {m.result.evidence?.length||0} preuves et {m.result.sources?.length||0} sources <ArrowUpRight size={15}/></button></>}</div></div>)}
          {loading&&<div className="message assistant"><div className="message-icon"><Bot size={18}/></div><div className="typing-indicator" role="status" aria-label="Investigation en cours"><i/><i/><i/></div></div>}
          <div ref={bottom}/>
        </div>
        {messages.length<=1&&<div className="suggestions"><span>QUESTIONS SUGGÉRÉES</span><div>{SUGGESTIONS.map(s=><button key={s} onClick={()=>send(s)}><Sparkles size={15}/>{s}</button>)}</div></div>}
        <form className="compose" onSubmit={e=>{e.preventDefault();send();}}><div className="compose-input"><MessageSquareText size={18}/><input aria-label="Question d’investigation" value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Pose une question aux données..." maxLength={2000}/><kbd>↵</kbd></div><button aria-label="Envoyer" type="submit" disabled={loading||!question.trim()} className="send-btn"><Send size={18}/></button></form>
        <div className="conversation-foot"><label className="checkline"><input type="checkbox" checked={useGraph} onChange={e=>setUseGraph(e.target.checked)}/> Utiliser LangGraph</label><span><CornerDownLeft size={13}/> Entrée pour envoyer</span></div>
      </div>
      <div className="right-rail">
        <Panel title="Services locaux" subtitle="État vérifié par FastAPI" action={<button className="evidence-link" onClick={()=>void refreshStatus()}>Actualiser</button>}>
          {status?<div className="service-status"><p><Pill variant={status.rag.index_ready?'good':'warn'}>Qdrant : {status.rag.index_ready?'index prêt':status.rag.status}</Pill></p><p>{status.rag.documents} documents · {status.rag.chunks} chunks · recherche configurée : {status.rag.configured_backend==='local'?'TF-IDF':status.rag.configured_backend}</p>{status.rag.diagnostic&&<p role="status">{status.rag.diagnostic.message} ({status.rag.diagnostic.error_type})</p>}<p><Pill variant={status.langgraph_available?'good':'warn'}>LangGraph : {status.langgraph_available?'installé':'absent'}</Pill></p><p><Pill variant={status.ollama.available?'good':'warn'}>Ollama : {status.ollama.available?'modèle disponible':status.ollama.configured?'indisponible':'désactivé'}</Pill></p><small>La disponibilité ne prouve pas l’utilisation. Le mode de chaque réponse indique les composants exécutés.</small></div>:<p className="page-subtitle">{statusError||'Vérification des services…'}</p>}
        </Panel>
        <Panel title="Gouvernance" subtitle="Périmètre de l’investigation"><div className="rail-points"><div><CheckCircle2 size={18}/><span>Accès SQL en lecture seule</span></div><div><CheckCircle2 size={18}/><span>Aucune commande système</span></div><div><CheckCircle2 size={18}/><span>Faits et hypothèses séparés</span></div><div><CheckCircle2 size={18}/><span>Extraits documentaires cités</span></div></div></Panel>
        <Panel title="Dossier de preuves" subtitle="Investigation sélectionnée">{selected?<><div className="proof-counts"><div><strong>{selected.evidence?.length||0}</strong><span>Faits SQL</span></div><div><strong>{selected.sources?.length||0}</strong><span>Chunks</span></div></div><div className="source-list"><div className="evidence-mode"><BrainCircuit size={15}/> {selected.mode}</div>
          <small className="correlation-id">Corrélation : {selected.correlation_id} · {selected.latency_ms?.toFixed(0)} ms</small>
          {selected.sql_proofs?.map(proof=><details key={proof.id} className="source-item" open><summary><FileSearch size={15}/>{proof.id} · {proof.tool}</summary><pre>{proof.query}</pre><p>Paramètres : {JSON.stringify(proof.parameters)}</p><div className="table-wrap"><table className="data-table"><thead><tr>{Object.keys(proof.rows[0]||{}).map(k=><th key={k}>{k}</th>)}</tr></thead><tbody>{proof.rows.map((row,i)=><tr key={i}>{Object.values(row).map((v,j)=><td key={j}>{String(v??'—')}</td>)}</tr>)}</tbody></table></div><small>{proof.row_count} ligne(s) · SQLite synthétique</small></details>)}
          {selected.sources?.map((source,i)=><details key={source.chunk_id||i} className="source-item"><summary><BookOpen size={15}/>{source.source.split('/').pop()}</summary><p>{source.backend} · score {source.score?.toFixed(4)} · lignes {source.start_line}–{source.end_line}</p><small className="correlation-id">Chunk {source.chunk_id}</small>{source.quarantined&&<Pill variant="warn">Exclu de la synthèse</Pill>}<p>{source.text}</p><button className="evidence-link" onClick={()=>void openDocument(source.source)}>Consulter le document complet <ArrowUpRight size={14}/></button></details>)}
          {documentLoading&&<p role="status">Chargement du runbook…</p>}{documentError&&<p role="alert">{documentError}</p>}{document&&<details className="source-item" open><summary>{document.source.split('/').pop()}</summary><pre className="runbook-text">{document.text}</pre></details>}
          <h4 className="workflow-title">Étapes réellement parcourues</h4><ol className="workflow-steps">{selected.steps?.map(step=><li key={step.node} className={step.status==='skipped'?'skipped':''}><span>{NODE_NAMES[step.node]||step.node}</span><small>{step.status==='skipped'?'sans outil':`${step.latency_ms.toFixed(1)} ms`}</small></li>)}</ol>
          <div className="report-limits"><b>Limites des conclusions</b>{selected.warnings?.map((w,i)=><p key={i}>{w}</p>)}</div>
        </div></>:<div className="empty-evidence"><FileSearch size={30}/><p>Les preuves, sources et étapes apparaîtront après une investigation.</p></div>}</Panel>
      </div>
    </div>
  </>;
}
