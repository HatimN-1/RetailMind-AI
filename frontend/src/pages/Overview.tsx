import { useState } from 'react';
import { Activity, AlertTriangle, ArrowUpRight, Banknote, Download, ReceiptText, RefreshCw, ShieldAlert } from 'lucide-react';
import { AreaChart, Area, BarChart, Bar, Cell, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, PieChart, Pie, Legend } from 'recharts';
import { api, exportCsv, integer, money, shortDay } from '../api';
import { useLoad } from '../hooks';
import type { Period, PageId } from '../types';
import { Metric, Panel, Pill, StatusNotice, TransactionTable } from '../components/UI';

const COLORS=['#9476fc','#27d3b5','#f5ab67','#53a9ed','#ee78b6','#98a3b9'];
const axis={fill:'#8192ad',fontSize:11};
const tooltipStyle={border:'1px solid #304061',backgroundColor:'#12223b',borderRadius:12,color:'#eaf0fc',fontSize:12};

export default function Overview({onNavigate}: {onNavigate:(p:PageId)=>void}) {
  const [period,setPeriod]=useState<Period>('all');
  const {data,loading,error,reload}=useLoad(()=>api.analytics(period),[period]);
  const {data:top}=useLoad(()=>api.alerts(new URLSearchParams({limit:'5',offset:'0',sort:'amount_desc'})),[]);
  if(loading && !data) return <StatusNotice message="Chargement des indicateurs..."/>;
  if(error && !data) return <StatusNotice kind="error" message={error} retry={reload}/>;
  if(!data) return null;
  const ratio=data.summary.orders?100*data.summary.anomalies/data.summary.orders:0;
  const daily=data.daily.slice(-30).map(row=>({...row,short:shortDay(row.day)}));
  const pie=data.categories.map((row,i)=>({name:row.category,value:row.revenue,fill:COLORS[i%COLORS.length]}));
  return <>
    <div className="page-title-row"><div><div className="eyebrow">WORKSPACE / EXECUTIVE OVERVIEW</div><h1>Vue exécutive<span className="heading-spark">✦</span></h1><p className="page-subtitle">Une vue instantanée de la performance commerciale et des risques simulés.</p></div>
    <div className="title-actions"><div className="segmented" role="group" aria-label="Période">{(['7d','30d','all'] as Period[]).map(p=><button className={period===p?'active':''} onClick={()=>setPeriod(p)} key={p}>{p==='all'?'Global':p==='7d'?'7 jours':'30 jours'}</button>)}</div><button className="icon-button" title="Actualiser" onClick={reload}><RefreshCw size={18}/></button></div></div>
    <div className="synthetic-line"><span className="green-pulse"/> Environnement de démonstration <span>•</span> Données 100 % synthétiques <span>•</span> Dernière date du jeu : {data.latest_day ?? 'N/A'}</div>
    <div className="metric-grid">
      <Metric label="Transactions analysées" value={integer(data.summary.orders)} hint="Commandes du périmètre sélectionné" icon={<ReceiptText size={19}/>} accent="violet"/>
      <Metric label="Revenus encaissés" value={money(data.summary.revenue_mad)} hint="Transactions marquées comme payées" icon={<Banknote size={19}/>} accent="teal"/>
      <Metric label="Anomalies simulées" value={integer(data.summary.anomalies)} hint={`${ratio.toFixed(1).replace('.',',')} % des transactions`} icon={<ShieldAlert size={19}/>} accent="amber"/>
      <Metric label="Paiements échoués" value={integer(data.summary.failed_payments)} hint="Statut du paiement : failed" icon={<Activity size={19}/>} accent="pink"/>
    </div>
    <div className="charts-grid">
      <Panel className="chart-primary" title="Évolution des encaissements" subtitle="Revenus journaliers (MAD), 30 derniers jours affichés" action={<Pill variant="good">Données SQL</Pill>}>
        <div className="chart-legend"><span className="legend-dot violet"/> Chiffre d'affaires encaissé</div>
        <div className="chart-holder"><ResponsiveContainer width="100%" height="100%"><AreaChart data={daily} margin={{top:10,right:6,left:-12,bottom:4}}><defs><linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#9178fa" stopOpacity={0.32}/><stop offset="100%" stopColor="#9178fa" stopOpacity={0}/></linearGradient></defs><CartesianGrid vertical={false} stroke="#263850" strokeDasharray="4 5"/><XAxis dataKey="short" tick={axis} tickLine={false} axisLine={false} interval="preserveStartEnd"/><YAxis tick={axis} tickLine={false} axisLine={false} tickFormatter={v=>`${Math.round(v/1000)}k`}/><Tooltip contentStyle={tooltipStyle} formatter={(v)=>money(Number(v))} labelFormatter={(v)=>`Jour : ${v}`}/><Area type="monotone" dataKey="revenue" stroke="#a18bff" strokeWidth={3} fill="url(#revenueGradient)" activeDot={{r:6}}/></AreaChart></ResponsiveContainer></div>
      </Panel>
      <Panel title="Répartition par catégorie" subtitle="Revenus encaissés par famille de produits" action={<span className="tiny-action">VENTES</span>}>
        <div className="donut-holder"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={pie} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={67} outerRadius={99} paddingAngle={3} stroke="none">{pie.map((p,i)=><Cell key={i} fill={p.fill}/>)}</Pie><Tooltip contentStyle={tooltipStyle} formatter={(v)=>money(Number(v))}/><Legend iconType="circle" iconSize={8} wrapperStyle={{fontSize:11,color:'#98a3bb'}}/></PieChart></ResponsiveContainer></div>
      </Panel>
    </div>
    <div className="charts-grid split-bottom">
      <Panel title="Performance par région" subtitle="Top des régions par revenus encaissés"><div className="chart-holder secondary-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.regions} margin={{left:-12,right:8,top:12,bottom:14}}><CartesianGrid vertical={false} stroke="#263850" strokeDasharray="4 5"/><XAxis dataKey="region" tick={axis} axisLine={false} tickLine={false}/><YAxis tick={axis} axisLine={false} tickLine={false} tickFormatter={v=>`${Math.round(v/1000)}k`}/><Tooltip contentStyle={tooltipStyle} formatter={(v)=>money(Number(v))}/><Bar dataKey="revenue" name="Revenus" fill="#42cbb9" radius={[7,7,0,0]} maxBarSize={42}/></BarChart></ResponsiveContainer></div></Panel>
      <Panel title="État des paiements" subtitle="Nombre de transactions par statut"><div className="payment-grid">{data.payments.map(row=><div className="payment-item" key={row.status}><span className={`payment-icon ${row.status}`}><span className="status-dot"/></span><div><b>{row.status==='paid'?'Paiements validés':row.status==='failed'?'Paiements échoués':'En attente'}</b><p>{row.status}</p></div><strong>{integer(row.orders)}</strong></div>)}</div><div className="insight-card"><AlertTriangle size={18}/><p><b>Note méthodologique</b> Les volumes et anomalies proviennent d'un générateur reproductible. Aucune fraude réelle n'est représentée.</p></div></Panel>
    </div>
    <Panel title="Transactions nécessitant une revue" subtitle="Plus grands montants parmi les labels d'anomalie injectés" action={<div className="panel-actions"><button className="text-action" onClick={()=>top && exportCsv(top.items as unknown as Record<string,unknown>[], 'retailmind_top_anomalies.csv')}><Download size={15}/> CSV</button><button className="text-action" onClick={()=>onNavigate('anomalies')}>Voir tout <ArrowUpRight size={16}/></button></div>}>
      <TransactionTable rows={top?.items || []} compact onSelect={()=>onNavigate('anomalies')}/>
    </Panel>
  </>;
}
