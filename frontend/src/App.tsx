import { useEffect, useState } from 'react';
import { Activity, Bell, BrainCircuit, ChartNoAxesCombined, ChevronDown, DatabaseZap, GitBranch, LayoutDashboard, Menu, Moon, PanelLeftClose, Search, Settings2, ShieldAlert, Sun, TableProperties, Wifi, WifiOff, X } from 'lucide-react';
import Overview from './pages/Overview';
import Transactions from './pages/Transactions';
import Anomalies from './pages/Anomalies';
import InvestigationPage from './pages/Investigation';
import Quality from './pages/Quality';
import Monitoring from './pages/Monitoring';
import { api } from './api';
import { useLoad } from './hooks';
import type { PageId } from './types';

const menu: Array<{id:PageId;title:string;desc:string;icon:typeof LayoutDashboard}>=[
  {id:'overview',title:'Vue exécutive',desc:'Analyse commerciale',icon:LayoutDashboard},
  {id:'transactions',title:'Transactions',desc:'Explorateur SQL',icon:TableProperties},
  {id:'anomalies',title:'Anomalies',desc:'Centre de surveillance',icon:ShieldAlert},
  {id:'investigation',title:'Investigation IA',desc:'Assistant gouverné',icon:BrainCircuit},
  {id:'quality',title:'Qualité & ML',desc:'Observabilité',icon:Activity},
  {id:'monitoring',title:'Pipelines V4',desc:'Suivi Airflow & dbt',icon:GitBranch},
];

export default function App() {
  const [page,setPage]=useState<PageId>('overview');
  const [sidebarOpen,setSidebarOpen]=useState(false);
  const [collapsed,setCollapsed]=useState(false);
  const [theme,setTheme]=useState<'dark'|'light'>(()=>localStorage.getItem('retailmind-theme')==='light'?'light':'dark');
  const {data:health,loading:healthLoading,reload:reloadHealth}=useLoad(()=>api.health(),[]);
  useEffect(()=>{document.documentElement.dataset.theme=theme;localStorage.setItem('retailmind-theme',theme)},[theme]);
  const navigate=(p:PageId)=>{setPage(p);setSidebarOpen(false);window.scrollTo({top:0,behavior:'smooth'})};
  return <div className={`app-shell ${collapsed?'collapsed':''}`}>
    <div className={`mobile-overlay ${sidebarOpen?'show':''}`} onClick={()=>setSidebarOpen(false)} />
    <aside className={`sidebar ${sidebarOpen?'mobile-open':''}`}>
      <div className="brand"><div className="brand-mark"><DatabaseZap size={23} strokeWidth={2.2}/></div><div className="brand-name"><b>RetailMind<span> AI</span></b><small>INTELLIGENCE PLATFORM</small></div><button className="sidebar-close" aria-label="Fermer le menu" onClick={()=>setSidebarOpen(false)}><X size={18}/></button></div>
      <div className="workspace-label"><span>WORKSPACE</span><button title="Réduire la navigation" onClick={()=>setCollapsed(c=>!c)}><PanelLeftClose size={17}/></button></div>
      <nav className="nav-main" aria-label="Navigation principale">{menu.map(item=>{const Icon=item.icon;return <button type="button" title={item.title} key={item.id} onClick={()=>navigate(item.id)} className={`nav-link ${page===item.id?'active':''}`}><Icon size={19} strokeWidth={1.9}/><div><span>{item.title}</span><small>{item.desc}</small></div>{page===item.id&&<i className="active-glow"/>}</button>})}</nav>
      <div className="sidebar-lower"><div className="workspace-label"><span>ENVIRONNEMENT</span></div><div className="environment-card"><div className="environment-top"><span className="green-pulse"/> <b>Laboratoire local</b></div><p>Transactions de démonstration, API en lecture seule et modèles expérimentaux.</p><span className="environment-tag">SANDBOX</span></div><div className="side-footer"><span className="avatar">HN</span><div><b>Portfolio · ENSA Fès</b><small>Hatim Nadir / 2026</small></div><Settings2 size={17}/></div></div>
    </aside>
    <div className="main-area"><header className="topbar"><div className="topbar-left"><button className="icon-button mobile-menu" aria-label="Afficher le menu" onClick={()=>setSidebarOpen(v=>!v)}><Menu size={22}/></button><div className="breadcrumb"><span>RetailMind AI</span><span className="slash">/</span><strong>{menu.find(x=>x.id===page)?.title}</strong></div></div>
      <div className="topbar-right"><button className="top-search" onClick={()=>navigate('transactions')}><Search size={16}/> <span>Explorer les données</span></button><button className="icon-button theme-button" aria-label="Changer le thème" title="Changer le thème" onClick={()=>setTheme(t=>t==='dark'?'light':'dark')}>{theme==='dark'?<Sun size={19}/>:<Moon size={19}/>}</button><button className="icon-button" aria-label="Actualiser la connexion" title="Actualiser la connexion" onClick={reloadHealth}><Bell size={19}/></button><span className="topbar-divider"/><div className="top-profile"><span>HN</span><ChevronDown size={14}/></div></div>
    </header>
    <main className="content"><div className="connection-strip"><div className={`connection-item ${health?.warehouse_ready?'online':''}`}>{health?.warehouse_ready?<Wifi size={14}/>:<WifiOff size={14}/>} {healthLoading?'Vérification du backend...':health?.warehouse_ready?'API FastAPI connectée':'API non connectée'}</div><div className="connection-second"><span className="dot-separator"/> Environnement Data & IA · Démonstration locale</div></div>
      {page==='overview'&&<Overview onNavigate={navigate}/>} {page==='transactions'&&<Transactions/>} {page==='anomalies'&&<Anomalies/>} {page==='investigation'&&<InvestigationPage/>} {page==='quality'&&<Quality/>} {page==='monitoring'&&<Monitoring/>}
    </main>
    <footer className="app-footer"><span><ChartNoAxesCombined size={14}/> RetailMind AI · Portfolio technique</span><span>Version 2.0 · Données synthétiques · Aucun usage en production</span></footer>
    </div>
  </div>;
}
