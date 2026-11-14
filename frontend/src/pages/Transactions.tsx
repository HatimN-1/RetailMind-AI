import { useState } from 'react';
import { Download, Filter, RefreshCw, Rows3, SlidersHorizontal } from 'lucide-react';
import { api, exportCsv, integer } from '../api';
import { useLoad } from '../hooks';
import type { SortKey, Transaction } from '../types';
import { Pager, Panel, SearchBox, StatusNotice, TransactionDrawer, TransactionTable } from '../components/UI';

export default function Transactions() {
  const [search,setSearch]=useState('');
  const [region,setRegion]=useState('');
  const [status,setStatus]=useState('');
  const [sort,setSort]=useState<SortKey>('recent');
  const [anomalyOnly,setAnomalyOnly]=useState(false);
  const [offset,setOffset]=useState(0);
  const [selected,setSelected]=useState<Transaction|null>(null);
  const limit=12;
  const query=new URLSearchParams({limit:String(limit),offset:String(offset),search,region,status,sort,anomaly_only:String(anomalyOnly)});
  const {data,loading,error,reload}=useLoad(()=>api.transactions(query),[search,region,status,sort,anomalyOnly,offset]);
  const setSearchReset=(x:string)=>{setSearch(x);setOffset(0);};
  return <>
    <div className="page-title-row"><div><div className="eyebrow">DATA EXPLORER / TRANSACTIONS</div><h1>Explorateur de transactions</h1><p className="page-subtitle">Parcours, recherche et inspection des données normalisées par le pipeline.</p></div><button className="btn btn-outline" onClick={reload}><RefreshCw size={17}/> Actualiser</button></div>
    <div className="synthetic-line"><span className="green-pulse"/> Vue SQL en lecture seule · Transactions fictives et anonymisées</div>
    <Panel className="full-panel" title="Registre des transactions" subtitle={`${data?integer(data.total):'…'} transactions correspondent aux filtres`} action={<div className="panel-actions"><button className="text-action" disabled={!data?.items.length} onClick={()=>data && exportCsv(data.items as unknown as Record<string,unknown>[], 'retailmind_transactions_page.csv')}><Download size={15}/> Exporter la page</button></div>}>
      <div className="filter-bar"><SearchBox value={search} onChange={setSearchReset} placeholder="ID, région ou catégorie..."/>
      <span className="filters-label"><SlidersHorizontal size={16}/> Filtres</span>
      <select aria-label="Région" value={region} onChange={e=>{setRegion(e.target.value);setOffset(0)}}><option value="">Toutes les régions</option>{['Casablanca','Rabat','Fes','Tanger','Marrakech','Agadir'].map(r=><option value={r} key={r}>{r}</option>)}</select>
      <select aria-label="Paiement" value={status} onChange={e=>{setStatus(e.target.value);setOffset(0)}}><option value="">Tous les paiements</option><option value="paid">Payées</option><option value="failed">Échouées</option><option value="pending">En attente</option></select>
      <select aria-label="Trier" value={sort} onChange={e=>{setSort(e.target.value as SortKey);setOffset(0)}}><option value="recent">Plus récentes</option><option value="oldest">Plus anciennes</option><option value="amount_desc">Montant décroissant</option><option value="amount_asc">Montant croissant</option></select>
      </div>
      <div className="quick-filter"><label className="checkline"><input type="checkbox" checked={anomalyOnly} onChange={e=>{setAnomalyOnly(e.target.checked);setOffset(0)}}/><span>Afficher uniquement les anomalies injectées</span></label><span className="muted-inline"><Filter size={14}/> {data?integer(data.total):'…'} éléments</span></div>
      {error?<StatusNotice kind="error" message={error} retry={reload}/>:loading?<StatusNotice message="Chargement des transactions..."/>:<TransactionTable rows={data?.items||[]} onSelect={setSelected}/>}
      {data && <Pager offset={offset} limit={limit} total={data.total} onPage={setOffset}/>}
    </Panel>
    <div className="footer-info"><Rows3 size={16}/> La recherche, le tri et la pagination sont exécutés côté FastAPI/SQLite, et non seulement dans le navigateur.</div>
    <TransactionDrawer t={selected} onClose={()=>setSelected(null)}/>
  </>;
}
