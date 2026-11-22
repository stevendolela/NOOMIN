import { Activity, ArrowDownRight, ArrowUpRight, Bell, ChevronDown, CircleHelp, Command, Database, LayoutDashboard, LifeBuoy, Plus, Search, Settings2, Sparkles, Users, Workflow } from 'lucide-react';
import { useState } from 'react';
import { Button } from './components/ui/button';

const navigation = [
  { label: 'Vue d’ensemble', icon: LayoutDashboard },
  { label: 'Sources de données', icon: Database },
  { label: 'Pipelines', icon: Workflow },
  { label: 'Analyses', icon: Activity },
];

function App() {
  const [active, setActive] = useState('Vue d’ensemble');
  const [notice, setNotice] = useState('');
  return <div className="shell">
    <aside className="sidebar">
      <a className="brand" href="#home" aria-label="NOOMIN accueil"><span className="brand-mark"><span/><span/><span/><span/></span><span>noomin</span></a>
      <button className="workspace-switch"><span className="workspace-avatar">N</span><span className="workspace-copy"><b>Votre espace</b><small>Organisation</small></span><ChevronDown size={15}/></button>
      <div className="side-label">ESPACE DE TRAVAIL</div>
      <nav aria-label="Navigation principale">{navigation.map(({label, icon: Icon}) => <button key={label} onClick={() => setActive(label)} className={`nav-item ${active === label ? 'selected' : ''}`}><Icon size={18}/><span>{label}</span>{label === 'Vue d’ensemble' && <span className="nav-dot"/>}</button>)}</nav>
      <div className="side-label connections-label">VOTRE ORGANISATION</div>
      <button className="nav-item" onClick={() => setNotice('La gestion des membres sera disponible après la configuration de l’organisation.')}><Users size={18}/><span>Membres</span></button>
      <button className="nav-item" onClick={() => setNotice('Les paramètres d’organisation seront disponibles dans une prochaine étape.')}><Settings2 size={18}/><span>Paramètres</span></button>
      <div className="sidebar-bottom"><div className="help-card"><div className="help-icon"><CircleHelp size={17}/></div><b>Besoin d’un coup de main ?</b><p>Explorez les ressources pour démarrer avec NOOMIN.</p><button onClick={() => setNotice('Le centre d’aide sera ajouté prochainement.')}>Découvrir le guide <ArrowUpRight size={14}/></button></div><button className="profile"><span className="profile-avatar">N</span><span className="profile-copy"><b>Nouvel espace</b><small>Administrateur</small></span><ChevronDown size={15}/></button></div>
    </aside>
    <main className="main" id="home">
      <header className="topbar"><div className="breadcrumbs"><span>Espace de travail</span><span className="crumb-divider">/</span><b>{active}</b></div><div className="top-actions"><button className="search-button" onClick={() => setNotice('La recherche sera disponible avec vos premières ressources.')}><Search size={16}/><span>Rechercher</span><kbd>⌘ K</kbd></button><button className="icon-button notification" aria-label="Notifications" onClick={() => setNotice('Vous n’avez pas encore de notification.')}><Bell size={18}/></button><span className="top-avatar">N</span></div></header>
      <div className="content">
        <div className="welcome-row"><div><div className="eyebrow"><span className="eyebrow-line"/>VOTRE ESPACE DE PILOTAGE</div><h1>Bonjour, bienvenue sur NOOMIN<span className="title-dot">.</span></h1><p className="subtitle">Tout commence par une bonne connexion à vos données.</p></div><Button size="sm" className="primary-button" onClick={() => setNotice('Connectez une source dès que le module d’intégration sera configuré.')}><Plus size={17}/> Connecter une source</Button></div>
        {notice && <div className="notice" role="status"><span>{notice}</span><button aria-label="Fermer" onClick={() => setNotice('')}>×</button></div>}
        <section className="welcome-card"><div className="welcome-text"><div className="welcome-badge"><Sparkles size={14}/> VOTRE ESPACE EST PRÊT</div><h2>Vos données,<br/><span>enfin réunies.</span></h2><p>Connectez votre première source pour commencer à construire une vision claire de votre activité.</p><button className="card-cta" onClick={() => setNotice('Connectez une source dès que le module d’intégration sera configuré.')}>Découvrir les sources <ArrowUpRight size={16}/></button></div><div className="orbital" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="orbit orbit-three"/><div className="orbit-core"><span className="brand-mark large"><span/><span/><span/><span/></span></div><span className="orbit-node node-one"><Database size={18}/></span><span className="orbit-node node-two"><Activity size={18}/></span><span className="orbit-node node-three"><Sparkles size={17}/></span><span className="orbit-node node-four"><Workflow size={18}/></span></div><div className="card-grain"/></section>
        <div className="section-heading"><div><h2>Votre activité</h2><p>Un aperçu apparaîtra ici quand vos données seront connectées.</p></div><button className="period-button" disabled>30 derniers jours <ChevronDown size={15}/></button></div>
        <div className="metrics-grid"><Metric icon={<Database size={17}/>} label="Sources connectées" value="—" note="Aucune source pour l’instant"/><Metric icon={<Workflow size={17}/>} label="Pipelines actifs" value="—" note="En attente de configuration"/><Metric icon={<Activity size={17}/>} label="Analyses créées" value="—" note="Votre espace est prêt à démarrer"/></div>
        <section className="empty-panel"><div className="empty-icon"><Command size={21}/></div><div className="empty-copy"><h3>Votre tableau de bord prend forme</h3><p>Les indicateurs et analyses s’afficheront ici après connexion de vos sources.</p></div><button className="secondary-button" onClick={() => setNotice('Aucune donnée à actualiser pour le moment.')}><ArrowDownRight size={15}/> En savoir plus</button></section>
        <footer><span>© 2026 NOOMIN</span><span className="footer-status">Aucune source connectée <span className="footer-divider">·</span> Environnement de démarrage</span><button onClick={() => setNotice('Le centre d’aide sera ajouté prochainement.')}><LifeBuoy size={14}/> Centre d’aide</button></footer>
      </div>
    </main>
  </div>;
}

function Metric({ icon, label, value, note }: { icon: React.ReactNode; label: string; value: string; note: string }) {
  return <article className="metric-card"><div className="metric-top"><span className="metric-icon">{icon}</span><span className="metric-label">{label}</span></div><div className="metric-value">{value}</div><div className="metric-note">{note}</div></article>;
}

export default App;
