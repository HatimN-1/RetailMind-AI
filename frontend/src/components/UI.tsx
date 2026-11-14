import type { ReactNode } from 'react';
import { ArrowDownRight, ArrowUpRight, AlertTriangle, CheckCircle2, ChevronLeft, ChevronRight, Database, RefreshCw, Search, X } from 'lucide-react';
import type { Transaction } from '../types';
import { integer, money } from '../api';

export function Panel({ title, subtitle, action, children, className = '' }: {
  title?: string; subtitle?: string; action?: ReactNode; children: ReactNode; className?: string;
}) {
  return <section className={`panel ${className}`}><div className="panel-head">
    <div>{title && <h3>{title}</h3>}{subtitle && <p>{subtitle}</p>}</div>{action}</div>{children}</section>;
}
export function Metric({ label, value, hint, icon, accent = 'violet' }: {label: string; value: string; hint: string; icon: ReactNode; accent?: 'violet'|'teal'|'amber'|'pink'}) {
  return <div className={`metric metric-${accent}`}><div className="metric-heading"><span>{label}</span><span className="metric-icon">{icon}</span></div><div className="metric-value">{value}</div><p>{hint}</p></div>;
}
export function Pill({children, variant='neutral'}: {children: ReactNode;variant?: 'neutral'|'good'|'warn'|'bad'|'purple'}) {
  return <span className={`pill pill-${variant}`}>{children}</span>;
}
export function PaymentPill({status}: {status:string}) {
  return <Pill variant={status === 'paid'?'good':status === 'failed'?'bad':'warn'}><span className="status-dot"/>{status === 'paid'?'Payée':status === 'failed'?'Échouée':'En attente'}</Pill>;
}
export function StatusNotice({ kind='loading', message, retry }: {kind?:'loading'|'error'|'empty';message:string;retry?:()=>void}) {
  const Icon = kind==='error'?AlertTriangle:kind==='empty'?Database:RefreshCw;
  return <div className="notice-state"><Icon size={23} className={kind==='loading'?'spinning':''}/><b>{message}</b>{retry && <button className="btn btn-soft" onClick={retry}>Réessayer</button>}</div>;
}
export function SearchBox({value,onChange,placeholder='Rechercher...'}: {value:string;onChange:(v:string)=>void;placeholder?:string}) {
  return <label className="search-field"><Search size={17}/><input aria-label="Recherche" value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder}/>{value && <button title="Effacer" onClick={()=>onChange('')}><X size={15}/></button>}</label>;
}
export function Pager({offset,limit,total,onPage}: {offset:number;limit:number;total:number;onPage:(offset:number)=>void}) {
  return <div className="pager"><span>{total===0?'0 résultat':`${integer(offset+1)}–${integer(Math.min(offset+limit,total))} sur ${integer(total)}`}</span><div className="pager-buttons"><button aria-label="Page précédente" disabled={offset===0} onClick={()=>onPage(Math.max(0,offset-limit))}><ChevronLeft size={17}/></button><button aria-label="Page suivante" disabled={offset+limit>=total} onClick={()=>onPage(offset+limit)}><ChevronRight size={17}/></button></div></div>;
}
export function TransactionTable({rows,onSelect,compact=false}: {rows:Transaction[];onSelect?:(t:Transaction)=>void;compact?:boolean}) {
  return <div className="table-wrap"><table className="data-table"><thead><tr><th>Transaction</th><th>Région</th>{!compact&&<th>Catégorie</th>}<th>Montant</th><th>Paiement</th><th>Diagnostic</th><th></th></tr></thead><tbody>{rows.map(t=><tr key={t.transaction_id} onClick={()=>onSelect?.(t)} className={onSelect?'clickable':''}>
    <td><span className="tx-icon">{t.transaction_id.slice(-2)}</span><span className="tx-title">{t.transaction_id}</span><small>{t.day}</small></td>
    <td>{t.region}</td>{!compact&&<td>{t.category}</td>}<td className="money-cell">{money(t.total_amount)}</td><td><PaymentPill status={t.payment_status}/></td><td>{t.is_anomaly?<Pill variant="warn">Injectée</Pill>:<Pill variant="neutral">Normale</Pill>}</td><td><ArrowUpRight size={16}/></td></tr>)}</tbody></table>{rows.length===0&&<div className="empty-table">Aucune transaction trouvée.</div>}</div>;
}
export function TransactionDrawer({t,onClose}: {t:Transaction|null;onClose:()=>void}) {
  if(!t) return null;
  return <div className="drawer-backdrop" onClick={onClose}><aside className="drawer" role="dialog" aria-modal="true" aria-label="Détails transaction" onClick={e=>e.stopPropagation()}>
    <div className="drawer-top"><div><small>DÉTAIL DE TRANSACTION</small><h2>{t.transaction_id}</h2></div><button aria-label="Fermer" className="icon-button" onClick={onClose}><X size={20}/></button></div>
    <div className="drawer-amount">{money(t.total_amount)}<p>Montant total enregistré</p></div>
    <div className="detail-row"><span>Statut de paiement</span><PaymentPill status={t.payment_status}/></div>
    <div className="detail-row"><span>Étiquette anomalie</span><Pill variant={t.is_anomaly?'warn':'good'}>{t.is_anomaly?t.anomaly_type:'aucune'}</Pill></div>
    {([['Date',t.day],['Région',t.region],['Catégorie',t.category],['Canal',t.channel],['Quantité',integer(t.quantity)],['Prix unitaire',money(t.unit_price)],['Remise',`${Math.round(t.discount_pct*100)} %`]] as [string,string][]).map(([k,v])=><div className="detail-row" key={k}><span>{k}</span><b>{v}</b></div>)}
    <div className="drawer-info"><AlertTriangle size={18}/><span>Les anomalies sont injectées dans un jeu synthétique. Elles ne constituent pas une preuve de fraude.</span></div>
    <button className="btn btn-primary full-width" onClick={onClose}><CheckCircle2 size={16}/> Terminer l'inspection</button>
  </aside></div>;
}
export function Delta({positive,label}: {positive:boolean; label:string}) {
  return <span className={`delta ${positive?'positive':'negative'}`}>{positive?<ArrowUpRight size={15}/>:<ArrowDownRight size={15}/>} {label}</span>;
}
