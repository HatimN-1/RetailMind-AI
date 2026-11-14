import { useState } from 'react';
import { AlertTriangle, Download, ScanEye, ShieldCheck, ShieldAlert } from 'lucide-react';
import { api, exportCsv, integer } from '../api';
import { useLoad } from '../hooks';
import type { Transaction } from '../types';
import { Metric, Pager, Panel, SearchBox, StatusNotice, TransactionDrawer, TransactionTable } from '../components/UI';

const TYPES: Record<string,string>={extreme_price:'Prix extrême',extreme_quantity:'Quantité extrême',excessive_discount:'Remise excessive',failed_high_value:'Paiement élevé échoué'};
export default function Anomalies() {
  const [type,setType]=useState('');
  const [region,setRegion]=useState('');
  const [search,setSearch]=useState('');
  const [offset,setOffset]=useState(0);
  const [selected,setSelected]=useState<Transaction|null>(null);
  const limit=12;
  const query=new URLSearchParams({limit:String(limit),offset:String(offset),search,region,anomaly_type:type,sort:'amount_desc'});
  const {data,loading,error,reload}=useLoad(()=>api.alerts(query),[type,region,search,offset]);
  const {data:all}=useLoad(()=>api.analytics('all'),[]);
  const fraction=all?.summary.orders ? (all.summary.anomalies/all.summary.orders)*100 : 0;
  return <>
    <div className="page-title-row"><div><div className="eyebrow">RISK MONITORING / ANOMALIES</div><h1>Centre des anomalies</h1><p className="page-subtitle">Exploration des cas atypiques injectés dans le simulateur e-commerce.</p></div><div className="header-pill"><ShieldCheck size={16}/> Lecture seule</div></div>
    <div className="alert-banner"><AlertTriangle size={20}/><div><b>Jeu synthétique à étiquettes connues.</b> Les anomalies ci-dessous ont été générées artificiellement. Ce ne sont ni des fraudes avérées, ni des alertes produites par un modèle ML.</div></div>
    <div className="metric-grid three">
      <Metric label="Anomalies injectées" value={integer(all?.summary.anomalies || 0)} hint="Étiquettes de simulation" icon={<ShieldAlert size={19}/>} accent="amber"/>
      <Metric label="Taux d'injection" value={`${fraction.toFixed(2).replace('.',',')} %`} hint="Part des transactions étiquetées" icon={<ScanEye size={19}/>} accent="violet"/>
      <Metric label="Types de scénarios" value={integer(all?.anomaly_types.length || 0)} hint="Catégories d'anomalies générées" icon={<ShieldCheck size={19}/>} accent="teal"/>
    </div>
    <Panel title="Typologie d'anomalies" subtitle="Sélectionne un scénario pour filtrer le registre"><div className="type-grid"><button className={`type-option ${type===''?'selected':''}`} onClick={()=>{setType('');setOffset(0)}}><span>Toutes</span><strong>{integer(all?.summary.anomalies||0)}</strong></button>{all?.anomaly_types.map(x=><button key={x.type} className={`type-option ${type===x.type?'selected':''}`} onClick={()=>{setType(x.type===type?'':x.type);setOffset(0)}}><span>{TYPES[x.type]||x.type}</span><strong>{integer(x.count)}</strong></button>)}</div></Panel>
    <Panel title="Investigations à mener" subtitle="Tri par montant décroissant; choisir une ligne pour voir les attributs" action={<button className="text-action" disabled={!data?.items.length} onClick={()=>data&&exportCsv(data.items as unknown as Record<string,unknown>[], 'retailmind_anomalies_page.csv')}><Download size={15}/> Exporter CSV</button>}>
      <div className="filter-bar"><SearchBox value={search} onChange={v=>{setSearch(v);setOffset(0)}} placeholder="Rechercher une transaction..."/><select aria-label="Région" value={region} onChange={e=>{setRegion(e.target.value);setOffset(0)}}><option value="">Toutes les régions</option>{['Casablanca','Rabat','Fes','Tanger','Marrakech','Agadir'].map(r=><option key={r} value={r}>{r}</option>)}</select><span className="muted-inline">{integer(data?.total||0)} cas</span></div>
      {error?<StatusNotice kind="error" message={error} retry={reload}/>:loading?<StatusNotice message="Chargement des anomalies..."/>:<TransactionTable rows={data?.items||[]} onSelect={setSelected}/>}
      {data&&<Pager offset={offset} limit={limit} total={data.total} onPage={setOffset}/>}
    </Panel>
    <TransactionDrawer t={selected} onClose={()=>setSelected(null)}/>
  </>;
}
