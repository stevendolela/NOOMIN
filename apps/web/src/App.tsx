import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Activity, ArrowLeft, ArrowUpRight, Bell, Check, ChevronDown, CircleHelp, ClipboardList, Database, FileSpreadsheet, KeyRound, LayoutDashboard, LoaderCircle, LogOut, Plus, Settings2, Sparkles, Table2, Trash2, Upload, Workflow } from 'lucide-react';
import AuthScreen from './components/AuthScreen';
import PipelineManager from './components/PipelineManager';
import AnalyticsManager from './components/AnalyticsManager';
import MemberManager from './components/MemberManager';
import InviteAccept from './components/InviteAccept';
import AuditLogManager from './components/AuditLogManager';
import ApiKeyManager from './components/ApiKeyManager';
import { Button } from './components/ui/button';
import { api } from './lib/api';
import type { ColumnProfile, Dataset, DatasetDetail, DatasetProfile, Session } from './lib/types';

type View = 'overview' | 'datasets' | 'pipelines' | 'analytics' | 'settings' | 'audit' | 'api_keys' | 'detail';

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}
function formatDate(value: string) { return new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium' }).format(new Date(value)); }

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [booting, setBooting] = useState(true);
  const [organizationId, setOrganizationId] = useState('');
  const [view, setView] = useState<View>('overview');
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [datasetDetail, setDatasetDetail] = useState<DatasetDetail | null>(null);
  const [datasetProfile, setDatasetProfile] = useState<DatasetProfile | null>(null);
  const [loadingData, setLoadingData] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState<{ text: string; kind: 'success' | 'error' } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const invitationToken = new URLSearchParams(window.location.search).get('invite') ?? new URLSearchParams(window.location.hash.replace(/^#/, '')).get('invite');

  useEffect(() => {
    let alive = true;
    api<Session>('/auth/session').then((data) => {
      if (!alive) return;
      setSession(data);
      setOrganizationId(data.organizations[0]?.id ?? '');
    }).catch(() => { if (alive) setSession(null); }).finally(() => { if (alive) setBooting(false); });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!organizationId) { setDatasets([]); return; }
    let alive = true;
    setLoadingData(true);
    api<Dataset[]>('/datasets', {}, organizationId).then((data) => { if (alive) setDatasets(data); })
      .catch((error) => { if (alive) setNotice({ text: error instanceof Error ? error.message : 'Impossible de charger les données.', kind: 'error' }); })
      .finally(() => { if (alive) setLoadingData(false); });
    return () => { alive = false; };
  }, [organizationId]);

  useEffect(() => {
    if (view !== 'detail' || !selectedDatasetId || !organizationId) return;
    let alive = true;
    setLoadingData(true); setDatasetDetail(null); setDatasetProfile(null);
    Promise.all([api<DatasetDetail>(`/datasets/${selectedDatasetId}`, {}, organizationId), api<DatasetProfile>(`/datasets/${selectedDatasetId}/profile`, {}, organizationId)])
      .then(([detail, profile]) => { if (alive) { setDatasetDetail(detail); setDatasetProfile(profile); } })
      .catch((error) => { if (alive) setNotice({ text: error instanceof Error ? error.message : 'Impossible d’ouvrir ce jeu de données.', kind: 'error' }); })
      .finally(() => { if (alive) setLoadingData(false); });
    return () => { alive = false; };
  }, [view, selectedDatasetId, organizationId]);

  const organization = useMemo(() => session?.organizations.find((item) => item.id === organizationId) ?? null, [session, organizationId]);
  const totalRows = datasets.reduce((sum, dataset) => sum + dataset.row_count, 0);
  const totalColumns = datasets.reduce((sum, dataset) => sum + dataset.column_count, 0);

  function authenticated(next: Session) {
    window.history.replaceState({}, '', window.location.pathname);
    setSession(next);
    setOrganizationId(next.organizations[0]?.id ?? '');
    setView('overview');
  }

  function updateInvitationSession(next: Session) {
    setSession(next);
    setOrganizationId(next.organizations[0]?.id ?? '');
  }

  function finishInvitation(next: Session) { authenticated(next); }
  function cancelInvitation() {
    window.history.replaceState({}, '', window.location.pathname);
    if (!session) setSession(null);
    else setView('overview');
  }

  async function logout() {
    try { await api<void>('/auth/logout', { method: 'POST' }); } finally {
      setSession(null); setOrganizationId(''); setDatasets([]); setDatasetDetail(null); setDatasetProfile(null); setView('overview');
    }
  }

  async function uploadSelected(file?: File) {
    if (!file || !organizationId) return;
    setNotice(null);
    const form = new FormData(); form.append('file', file);
    setUploading(true);
    try {
      const dataset = await api<Dataset>('/datasets', { method: 'POST', body: form }, organizationId);
      setDatasets((current) => [dataset, ...current]);
      setSelectedDatasetId(dataset.id); setView('detail'); setNotice({ text: `${dataset.name} a été importé : ${dataset.row_count.toLocaleString('fr-FR')} lignes analysables.`, kind: 'success' });
    } catch (error) {
      setNotice({ text: error instanceof Error ? error.message : 'Import impossible.', kind: 'error' });
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = '';
    }
  }

  function openDataset(id: string) { setSelectedDatasetId(id); setView('detail'); }

  async function deleteDataset(dataset: Dataset) {
    const confirmed = window.confirm(`Supprimer « ${dataset.name} » ? Les lignes importées, analyses enregistrées et pipelines qui utilisent ce jeu de données seront supprimés. Cette action est irréversible.`);
    if (!confirmed) return;
    try {
      await api<void>(`/datasets/${dataset.id}`, { method: 'DELETE' }, organizationId);
      setDatasets((current) => current.filter((item) => item.id !== dataset.id));
      setNotice({ text: `« ${dataset.name} » a été supprimé.`, kind: 'success' });
    } catch (error) {
      setNotice({ text: error instanceof Error ? error.message : 'Impossible de supprimer ce jeu de données.', kind: 'error' });
    }
  }

  if (booting) return <div className="boot-screen"><LoaderCircle className="spin" size={25}/><span>Ouverture de votre espace…</span></div>;
  if (invitationToken) return <InviteAccept token={invitationToken} session={session} onAccepted={finishInvitation} onLogin={updateInvitationSession} onCancel={cancelInvitation}/>;
  if (!session) return <AuthScreen onAuthenticated={authenticated}/>;

  const viewTitle = view === 'overview' ? 'Vue d’ensemble' : view === 'datasets' ? 'Jeux de données' : view === 'detail' ? (datasetDetail?.name ?? 'Jeu de données') : view === 'pipelines' ? 'Pipelines' : view === 'analytics' ? 'Analyses' : view === 'settings' ? 'Accès et membres' : view === 'audit' ? 'Journal d’audit' : view === 'api_keys' ? 'Accès API' : 'Paramètres';
  const canUpload = organization?.role !== 'viewer';
  const canManageMembers = organization?.role === 'owner' || organization?.role === 'admin';

  return <div className="shell app-shell">
    <input ref={fileInput} className="visually-hidden" type="file" accept=".csv,text/csv" onChange={(event) => void uploadSelected(event.target.files?.[0])}/>
    <aside className="sidebar">
      <a className="brand" href="#home" onClick={() => setView('overview')} aria-label="NOOMIN accueil"><span className="brand-mark"><span/><span/><span/><span/></span><span>noomin</span></a>
      <label className="workspace-switch"><span className="workspace-avatar">{organization?.name.slice(0, 1).toUpperCase() ?? 'N'}</span><span className="workspace-copy"><b>{organization?.name ?? 'Votre espace'}</b><small>{organization?.role === 'owner' ? 'Propriétaire' : organization?.role === 'admin' ? 'Administrateur' : organization?.role === 'member' ? 'Analyste' : 'Lecteur'}</small></span><select aria-label="Organisation active" value={organizationId} onChange={(event) => { setOrganizationId(event.target.value); setView('overview'); setSelectedDatasetId(''); setDatasetDetail(null); }} disabled={(session?.organizations.length ?? 0) < 2}>{session?.organizations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select><ChevronDown size={15}/></label>
      <div className="side-label">ESPACE DE TRAVAIL</div>
      <nav aria-label="Navigation principale">
        <NavItem label="Vue d’ensemble" active={view === 'overview'} onClick={() => setView('overview')} icon={<LayoutDashboard size={18}/>}/>
        <NavItem label="Jeux de données" active={view === 'datasets' || view === 'detail'} onClick={() => setView('datasets')} icon={<Database size={18}/>}/>
        <NavItem label="Pipelines" active={view === 'pipelines'} onClick={() => setView('pipelines')} icon={<Workflow size={18}/>}/>
        <NavItem label="Analyses" active={view === 'analytics'} onClick={() => setView('analytics')} icon={<Activity size={18}/>}/>
      </nav>
      <div className="side-label connections-label">ORGANISATION</div>
      <button aria-label="Accès et membres" className={`org-nav-row ${view === 'settings' ? 'selected' : ''}`} onClick={() => setView('settings')}><Settings2 size={17}/><span>Accès et membres</span></button>
      {organization?.role === 'owner' && <button aria-label="Accès API" className={`org-nav-row ${view === 'api_keys' ? 'selected' : ''}`} onClick={() => setView('api_keys')}><KeyRound size={17}/><span>Accès API</span></button>}
      {canManageMembers && <button aria-label="Journal d’audit" className={`org-nav-row ${view === 'audit' ? 'selected' : ''}`} onClick={() => setView('audit')}><ClipboardList size={17}/><span>Journal d’audit</span></button>}
      <div className="sidebar-bottom"><div className="help-card"><div className="help-icon"><CircleHelp size={17}/></div><b>Un espace qui grandit avec vous</b><p>Importez un premier fichier CSV pour explorer vos données.</p><button onClick={() => canUpload && fileInput.current?.click()}>Importer un CSV <ArrowUpRight size={14}/></button></div><button className="profile" onClick={() => void logout()} title="Se déconnecter"><span className="profile-avatar">{session.user.full_name.slice(0, 1).toUpperCase()}</span><span className="profile-copy"><b>{session.user.full_name}</b><small>{session.user.email}</small></span><LogOut size={15}/></button></div>
    </aside>
    <main className="main" id="home">
      <header className="topbar"><div className="breadcrumbs"><span>{organization?.name ?? 'Espace de travail'}</span><span className="crumb-divider">/</span><b>{viewTitle}</b></div><div className="top-actions"><span className="environment-chip"><i/> Espace privé</span><button className="icon-button notification" aria-label="Notifications" onClick={() => setNotice({ text: 'Aucune notification pour le moment.', kind: 'success' })}><Bell size={18}/></button><span className="top-avatar">{session.user.full_name.slice(0, 1).toUpperCase()}</span></div></header>
      <div className="content app-content">
        {notice && <div className={`notice ${notice.kind === 'error' ? 'notice-error' : ''}`} role="status"><span>{notice.text}</span><button aria-label="Fermer" onClick={() => setNotice(null)}>×</button></div>}
        {view === 'overview' && <>
          <div className="welcome-row"><div><div className="eyebrow"><span className="eyebrow-line"/>VOTRE ESPACE DE PILOTAGE</div><h1>Bonjour, {session.user.full_name.split(' ')[0]}<span className="title-dot">.</span></h1><p className="subtitle">Vos données d’activité, au même endroit.</p></div>{canUpload && <Button size="sm" className="primary-button" disabled={uploading} onClick={() => fileInput.current?.click()}>{uploading ? <LoaderCircle className="spin" size={17}/> : <Plus size={17}/>} Importer un CSV</Button>}</div>
          <section className="welcome-card"><div className="welcome-text"><div className="welcome-badge"><Sparkles size={14}/> BIENVENUE DANS VOTRE ESPACE</div><h2>Vos données,<br/><span>enfin réunies.</span></h2><p>Importez un fichier CSV pour commencer à explorer vos indicateurs et préparer vos analyses.</p>{canUpload && <button className="card-cta" onClick={() => fileInput.current?.click()}>Importer votre premier fichier <ArrowUpRight size={16}/></button>}</div><div className="orbital" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="orbit orbit-three"/><div className="orbit-core"><span className="brand-mark large"><span/><span/><span/><span/></span></div><span className="orbit-node node-one"><Database size={18}/></span><span className="orbit-node node-two"><Activity size={18}/></span><span className="orbit-node node-three"><Sparkles size={17}/></span><span className="orbit-node node-four"><Workflow size={18}/></span></div><div className="card-grain"/></section>
          <div className="section-heading"><div><h2>Votre activité</h2><p>Indicateurs calculés à partir des fichiers que vous avez importés.</p></div></div>
          <div className="metrics-grid"><Metric icon={<Database size={17}/>} label="Jeux de données" value={datasets.length.toLocaleString('fr-FR')} note="Fichiers CSV importés"/><Metric icon={<Table2 size={17}/>} label="Lignes disponibles" value={totalRows.toLocaleString('fr-FR')} note="Lignes conservées dans votre espace"/><Metric icon={<Activity size={17}/>} label="Colonnes importées" value={totalColumns.toLocaleString('fr-FR')} note="Champs détectés dans vos fichiers"/></div>
          <section className="dataset-section"><div className="section-heading"><div><h2>Vos derniers jeux de données</h2><p>Les fichiers importés dans cette organisation.</p></div><button className="text-action" onClick={() => setView('datasets')}>Tout afficher <ArrowUpRight size={14}/></button></div>{loadingData ? <LoadingPanel/> : datasets.length ? <DatasetTable datasets={datasets.slice(0, 5)} onOpen={openDataset} onDelete={deleteDataset} canDelete={canUpload}/> : <EmptyDatasets canUpload={canUpload} onUpload={() => fileInput.current?.click()}/>}</section>
        </>}
        {view === 'datasets' && <><PageHeading eyebrow="VOS DONNÉES" title="Jeux de données" description="Importez un fichier CSV, puis consultez les lignes conservées dans votre espace." action={canUpload ? <Button size="sm" className="primary-button" disabled={uploading} onClick={() => fileInput.current?.click()}>{uploading ? <LoaderCircle className="spin" size={17}/> : <Upload size={16}/>} Importer un CSV</Button> : undefined}/>{loadingData ? <LoadingPanel/> : datasets.length ? <DatasetTable datasets={datasets} onOpen={openDataset} onDelete={deleteDataset} canDelete={canUpload}/> : <EmptyDatasets canUpload={canUpload} onUpload={() => fileInput.current?.click()}/>}</>}
        {view === 'detail' && <>{datasetDetail ? <><button className="back-link" onClick={() => setView('datasets')}><ArrowLeft size={15}/> Retour aux jeux de données</button><PageHeading eyebrow="JEU DE DONNÉES CSV" title={datasetDetail.name} description={`${datasetDetail.original_filename} · Importé le ${formatDate(datasetDetail.created_at)}`} action={<span className="source-badge"><Check size={14}/> Import terminé</span>}/><div className="detail-metrics"><Metric icon={<Table2 size={17}/>} label="Lignes" value={datasetDetail.row_count.toLocaleString('fr-FR')} note="Lignes conservées"/><Metric icon={<Database size={17}/>} label="Colonnes" value={datasetDetail.column_count.toLocaleString('fr-FR')} note={datasetDetail.columns.join(' · ')}/><Metric icon={<FileSpreadsheet size={17}/>} label="Taille du fichier" value={formatBytes(datasetDetail.byte_size)} note="Fichier CSV d’origine"/></div><div className="preview-heading"><div><h2>Aperçu des données</h2><p>Les {datasetDetail.preview.length.toLocaleString('fr-FR')} premières lignes de ce fichier.</p></div></div><DataPreview dataset={datasetDetail}/><ProfilePanel profile={datasetProfile} loading={loadingData}/></> : <LoadingPanel/>}</>}
        {view === 'pipelines' && organizationId && <PipelineManager organizationId={organizationId} datasets={datasets} canEdit={canUpload} onOutput={async () => { setDatasets(await api<Dataset[]>('/datasets', {}, organizationId)); }} onNotice={(text, kind) => setNotice({ text, kind })}/>}
        {view === 'analytics' && organizationId && <AnalyticsManager organizationId={organizationId} datasets={datasets} canEdit={canUpload} onNotice={(text, kind) => setNotice({ text, kind })}/>}
        {view === 'settings' && organizationId && <MemberManager organizationId={organizationId} currentUserId={session.user.id} canManage={Boolean(canManageMembers)} role={organization?.role ?? ''} onNotice={(text, kind) => setNotice({ text, kind })}/>}
        {view === 'audit' && organizationId && <AuditLogManager organizationId={organizationId} onNotice={(text, kind) => setNotice({ text, kind })}/>}
        {view === 'api_keys' && organizationId && organization?.role === 'owner' && <ApiKeyManager organizationId={organizationId} onNotice={(text, kind) => setNotice({ text, kind })}/>}
        <footer className="app-footer"><span>© 2026 NOOMIN</span><span className="footer-status">{datasets.length ? `${datasets.length.toLocaleString('fr-FR')} jeu${datasets.length > 1 ? 'x' : ''} de données importé${datasets.length > 1 ? 's' : ''}` : 'Aucune source connectée'} <span className="footer-divider">·</span> Environnement de démarrage</span><button onClick={() => setNotice({ text: 'Le centre d’aide sera ajouté prochainement.', kind: 'success' })}><CircleHelp size={14}/> Centre d’aide</button></footer>
      </div>
    </main>
  </div>;
}

function NavItem({ label, active, onClick, icon, soon = false }: { label: string; active: boolean; onClick: () => void; icon: ReactNode; soon?: boolean }) {
  return <button onClick={onClick} className={`nav-item ${active ? 'selected' : ''}`}><span className="nav-icon">{icon}</span><span>{label}</span>{soon && <span className="nav-soon">Bientôt</span>}</button>;
}
function Metric({ icon, label, value, note }: { icon: ReactNode; label: string; value: string; note: string }) {
  return <article className="metric-card"><div className="metric-top"><span className="metric-icon">{icon}</span><span className="metric-label">{label}</span></div><div className="metric-value">{value}</div><div className="metric-note">{note}</div></article>;
}
function PageHeading({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>{eyebrow}</div><h1>{title}</h1><p className="subtitle">{description}</p></div>{action}</div>;
}
function DatasetTable({ datasets, onOpen, onDelete, canDelete }: { datasets: Dataset[]; onOpen: (id: string) => void; onDelete: (dataset: Dataset) => void; canDelete: boolean }) {
  return <div className="data-table-wrap"><table className="data-table"><thead><tr><th>JEU DE DONNÉES</th><th>LIGNES</th><th>COLONNES</th><th>TAILLE</th><th>IMPORTÉ LE</th><th/></tr></thead><tbody>{datasets.map((dataset) => <tr key={dataset.id} onClick={() => onOpen(dataset.id)} tabIndex={0} onKeyDown={(event) => event.key === 'Enter' && onOpen(dataset.id)}><td><span className="dataset-file-icon"><FileSpreadsheet size={17}/></span><span className="dataset-name-cell"><b>{dataset.name}</b><small>{dataset.original_filename}</small></span></td><td>{dataset.row_count.toLocaleString('fr-FR')}</td><td>{dataset.column_count.toLocaleString('fr-FR')}</td><td>{formatBytes(dataset.byte_size)}</td><td>{formatDate(dataset.created_at)}</td><td className="dataset-actions"><ArrowUpRight size={16}/>{canDelete && <button className="delete-dataset-button" title={`Supprimer ${dataset.name}`} aria-label={`Supprimer ${dataset.name}`} onClick={(event) => { event.stopPropagation(); onDelete(dataset); }}><Trash2 size={15}/></button>}</td></tr>)}</tbody></table></div>;
}
function DataPreview({ dataset }: { dataset: DatasetDetail }) {
  if (!dataset.preview.length) return <div className="empty-preview"><Table2 size={22}/><b>Le fichier ne contient aucune ligne de données.</b><span>Les en-têtes ont été importés et conservés.</span></div>;
  return <div className="data-table-wrap preview-wrap"><table className="data-table preview-table"><thead><tr><th>#</th>{dataset.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead><tbody>{dataset.preview.map((row, index) => <tr key={index}><td className="row-index">{index + 1}</td>{dataset.columns.map((column) => <td key={column} title={row[column] ?? ''}>{row[column] ?? <span className="null-cell">—</span>}</td>)}</tr>)}</tbody></table></div>;
}
function EmptyDatasets({ canUpload, onUpload }: { canUpload: boolean; onUpload: () => void }) {
  return <div className="empty-datasets"><div className="empty-icon"><FileSpreadsheet size={21}/></div><h3>Aucun jeu de données pour le moment</h3><p>{canUpload ? 'Importez un fichier CSV pour commencer à explorer vos données.' : 'Un membre avec les droits de modification peut importer le premier fichier.'}</p>{canUpload && <Button size="sm" className="primary-button" onClick={onUpload}><Upload size={15}/> Choisir un fichier CSV</Button>}<small>CSV · UTF-8 · jusqu’à 10 Mo et 20 000 lignes</small></div>;
}
function LoadingPanel() { return <div className="loading-panel"><LoaderCircle size={19} className="spin"/> Chargement des données…</div>; }
function ProfilePanel({ profile, loading }: { profile: DatasetProfile | null; loading: boolean }) {
  if (loading || !profile) return <section className="profile-section"><div className="preview-heading"><div><h2>Profil des colonnes</h2><p>Calculé sur les valeurs réellement importées.</p></div></div><div className="loading-panel"><LoaderCircle size={18} className="spin"/> Calcul du profil…</div></section>;
  const numeric = profile.columns.filter((column) => column.data_type === 'number');
  return <section className="profile-section"><div className="preview-heading"><div><h2>Profil des colonnes</h2><p>Statistiques descriptives calculées sur les {profile.row_count.toLocaleString('fr-FR')} lignes importées.</p></div></div>{numeric.length > 0 && <div className="profile-grid">{numeric.map((column) => <NumericProfile key={column.name} column={column}/>)}</div>}<div className="column-profiles">{profile.columns.map((column) => <div className="column-profile-row" key={column.name}><span className="profile-type-icon">{column.data_type === 'number' ? <Activity size={15}/> : <Table2 size={15}/>}</span><b>{column.name}</b><span className="type-pill">{column.data_type === 'number' ? 'Numérique' : 'Texte'}</span><span className="column-profile-stat">{column.non_null_count.toLocaleString('fr-FR')} valeurs</span><span className="column-profile-stat">{column.unique_count.toLocaleString('fr-FR')} distinctes</span></div>)}</div>{numeric.length === 0 && <p className="no-numeric-note">Aucune colonne numérique détectée dans les lignes importées.</p>}</section>;
}

function NumericProfile({ column }: { column: ColumnProfile }) {
  const maxCount = Math.max(1, ...column.distribution.map((bin) => bin.count));
  return <article className="numeric-profile"><div className="numeric-profile-top"><div><span className="metric-label">DISTRIBUTION · {column.name}</span><h3>{column.name}</h3></div><span className="type-pill">Numérique</span></div><div className="distribution-bars" role="img" aria-label={`Distribution des valeurs de ${column.name}`}>{column.distribution.map((bin, index) => <div className="distribution-bin" key={index} title={`${bin.count} valeur${bin.count === 1 ? '' : 's'} entre ${bin.start} et ${bin.end}`}><span style={{height: `${Math.max(4, bin.count / maxCount * 82)}px`}}/><small>{bin.count}</small></div>)}</div><div className="distribution-range"><span>{column.minimum}</span><span>{column.maximum}</span></div><div className="numeric-profile-footer"><span>Moyenne <b>{column.average?.toLocaleString('fr-FR', {maximumFractionDigits: 2})}</b></span><span>{column.non_null_count.toLocaleString('fr-FR')} valeurs</span></div></article>;
}
