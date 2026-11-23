import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react';
import { Activity, BarChart3, Check, Database, FileSpreadsheet, LoaderCircle, Plus, Rows3, Sparkles } from 'lucide-react';
import { api } from '../lib/api';
import { Button } from './ui/button';
import type { ColumnProfile, Dataset, DatasetProfile, SavedAnalysis } from '../lib/types';

type Props = { organizationId: string; datasets: Dataset[]; canEdit: boolean; onNotice: (message: string, kind: 'success' | 'error') => void };

export default function AnalyticsManager({ organizationId, datasets, canEdit, onNotice }: Props) {
  const [analyses, setAnalyses] = useState<SavedAnalysis[]>([]);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [datasetId, setDatasetId] = useState('');
  const [columnName, setColumnName] = useState('');
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(true);
  const [profileLoading, setProfileLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const selectedDataset = datasets.find((dataset) => dataset.id === datasetId);
  const activeColumn = profile?.columns.find((column) => column.name === columnName) ?? null;
  const numericColumns = useMemo(() => profile?.columns.filter((column) => column.data_type === 'number') ?? [], [profile]);
  const numericCount = numericColumns.length;
  const textCount = (profile?.columns.length ?? 0) - numericCount;
  const completeness = profile && profile.row_count && profile.columns.length
    ? Math.round(profile.columns.reduce((sum, column) => sum + column.non_null_count, 0) / (profile.row_count * profile.columns.length) * 100)
    : 0;

  async function loadAnalyses() {
    setLoading(true);
    try { setAnalyses(await api<SavedAnalysis[]>('/analyses', {}, organizationId)); }
    catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible de charger les analyses.', 'error'); }
    finally { setLoading(false); }
  }
  useEffect(() => { void loadAnalyses(); }, [organizationId]);
  useEffect(() => { if ((!datasetId || !datasets.some((dataset) => dataset.id === datasetId)) && datasets.length) setDatasetId(datasets[0].id); }, [datasets, datasetId]);
  useEffect(() => {
    if (!datasetId) { setProfile(null); setColumnName(''); return; }
    let alive = true;
    setProfile(null); setColumnName(''); setProfileLoading(true);
    api<DatasetProfile>(`/datasets/${datasetId}/profile`, {}, organizationId).then((value) => {
      if (alive) { setProfile(value); setColumnName(value.columns[0]?.name ?? ''); }
    }).catch((error) => { if (alive) onNotice(error instanceof Error ? error.message : 'Impossible de profiler ce jeu de données.', 'error'); })
      .finally(() => { if (alive) setProfileLoading(false); });
    return () => { alive = false; };
  }, [datasetId, organizationId]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!datasetId || !activeColumn || activeColumn.data_type !== 'number') return;
    setSaving(true);
    try {
      await api<SavedAnalysis>('/analyses', { method: 'POST', body: JSON.stringify({ title: title.trim() || `Distribution de ${activeColumn.name}`, dataset_id: datasetId, column_name: activeColumn.name }) }, organizationId);
      setTitle(''); await loadAnalyses(); onNotice('Analyse enregistrée à partir des valeurs du fichier.', 'success');
    } catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible d’enregistrer cette analyse.', 'error'); }
    finally { setSaving(false); }
  }

  if (!datasets.length) return <>
    <PageIntro/>
    <div className="empty-datasets"><div className="empty-icon"><BarChart3 size={21}/></div><h3>Importez un jeu de données pour commencer</h3><p>NOOMIN profilera les colonnes et construira des visualisations à partir des lignes réelles du CSV.</p></div>
  </>;

  return <>
    <PageIntro/>
    <section className="analytics-source-bar"><div className="analytics-source-label"><span className="analytics-source-icon"><Database size={16}/></span><span><b>Source analysée</b><small>Les indicateurs se recalculent à partir de l’import sélectionné.</small></span></div><select aria-label="Choisir un jeu de données" value={datasetId} onChange={(event) => setDatasetId(event.target.value)}>{datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name} · {dataset.row_count.toLocaleString('fr-FR')} lignes</option>)}</select><span className="analysis-source-chip"><i/> CSV importé</span></section>

    {profileLoading || !profile ? <div className="loading-panel analytics-loading"><LoaderCircle size={19} className="spin"/> Profil des colonnes en cours de calcul…</div> : <>
      <div className="analytics-kpi-grid">
        <AnalyticsKpi icon={<Rows3 size={17}/>} label="Lignes analysées" value={profile.row_count.toLocaleString('fr-FR')} detail={selectedDataset?.original_filename ?? 'Jeu de données'} tone="blue"/>
        <AnalyticsKpi icon={<Database size={17}/>} label="Champs détectés" value={profile.columns.length.toLocaleString('fr-FR')} detail={`${numericCount} numériques · ${textCount} texte`} tone="cyan"/>
        <AnalyticsKpi icon={<Check size={17}/>} label="Complétude" value={`${completeness}%`} detail="Valeurs renseignées" tone="green"/>
        <AnalyticsKpi icon={<BarChart3 size={17}/>} label="Analyses sauvegardées" value={analyses.length.toLocaleString('fr-FR')} detail="Dans cette organisation" tone="violet"/>
      </div>

      <div className="analytics-workspace">
        <section className="analytics-chart-card">
          <div className="analytics-section-header"><div><div className="analytics-overline"><Activity size={13}/> EXPLORATION</div><h2>{activeColumn?.data_type === 'number' ? 'Distribution des valeurs' : 'Répartition des valeurs'}</h2><p>{selectedDataset?.name} <span>·</span> {activeColumn?.name ?? 'Choisir un champ'}</p></div><label className="chart-field-select"><span>Champ analysé</span><select value={columnName} onChange={(event) => setColumnName(event.target.value)}>{profile.columns.map((column) => <option value={column.name} key={column.name}>{column.name} · {column.data_type === 'number' ? 'numérique' : 'texte'}</option>)}</select></label></div>
          {activeColumn?.data_type === 'number' ? <NumericChart column={activeColumn}/> : activeColumn ? <CategoryChart column={activeColumn}/> : <div className="analytics-no-column">Aucun champ disponible dans cet import.</div>}
          {activeColumn?.data_type === 'number' && <div className="analytics-chart-stats"><ChartStat label="Minimum" value={formatNumber(activeColumn.minimum)}/><ChartStat label="Moyenne" value={formatNumber(activeColumn.average)}/><ChartStat label="Maximum" value={formatNumber(activeColumn.maximum)}/><ChartStat label="Valeurs distinctes" value={activeColumn.unique_count.toLocaleString('fr-FR')}/></div>}
          {canEdit && activeColumn?.data_type === 'number' && <form onSubmit={save} className="analytics-save-form"><div><label htmlFor="analysis-title">Enregistrer cette vue</label><input id="analysis-title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder={`Distribution de ${activeColumn.name}`} maxLength={160}/></div><Button size="sm" className="primary-button" disabled={saving}>{saving ? <LoaderCircle size={15} className="spin"/> : <Plus size={15}/>} Enregistrer</Button></form>}
        </section>

        <section className="analytics-profile-card"><div className="analytics-section-header compact"><div><div className="analytics-overline"><FileSpreadsheet size={13}/> PROFIL DU FICHIER</div><h2>Champs détectés</h2><p>{profile.columns.length} champs · {profile.row_count.toLocaleString('fr-FR')} lignes source</p></div></div><div className="analytics-field-list">{profile.columns.map((column) => <button key={column.name} className={`analytics-field-row ${column.name === columnName ? 'is-active' : ''}`} onClick={() => setColumnName(column.name)}><span className={`field-type-mark ${column.data_type}`}>{column.data_type === 'number' ? '123' : 'Aa'}</span><span className="field-row-main"><b title={column.name}>{column.name}</b><small>{column.data_type === 'number' ? 'Numérique' : 'Texte'} · {column.unique_count.toLocaleString('fr-FR')} distinctes</small><span className="field-completeness"><i style={{width: `${profile.row_count ? column.non_null_count / profile.row_count * 100 : 0}%`}}/></span></span><span className="field-completeness-value">{profile.row_count ? Math.round(column.non_null_count / profile.row_count * 100) : 0}%</span></button>)}</div><div className="field-list-footnote"><Check size={13}/> Profil calculé sur les données importées</div></section>
      </div>
    </>}

    <section className="saved-analyses analytics-saved-section"><div className="pipeline-list-heading"><div><div className="analytics-overline"><Sparkles size={13}/> RAPPORTS CONSERVÉS</div><h2>Analyses enregistrées</h2><p>Retrouvez les distributions numériques sauvegardées dans cette organisation.</p></div><span className="saved-count-pill">{analyses.length} rapport{analyses.length === 1 ? '' : 's'}</span></div>{loading ? <div className="loading-panel"><LoaderCircle size={18} className="spin"/> Chargement…</div> : analyses.length ? <div className="saved-analysis-grid">{analyses.map((analysis) => <SavedDistribution key={analysis.id} analysis={analysis}/>)}</div> : <div className="pipeline-empty analytics-empty-saved"><div className="empty-icon"><BarChart3 size={20}/></div><h3>Aucun rapport sauvegardé</h3><p>Sélectionnez un champ numérique et enregistrez sa distribution depuis l’explorateur.</p></div>}</section>
    <div className="pipeline-capability-note"><Activity size={14}/> Ces visualisations sont calculées à partir des imports réels. L’assistant IA et les tableaux de bord composables ne sont pas activés.</div>
  </>;
}

function PageIntro() {
  return <div className="page-heading analytics-page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>BUSINESS INTELLIGENCE</div><h1>Analyses & insights</h1><p className="subtitle">Explorez la qualité, la structure et la distribution de vos données.</p></div><span className="analysis-source-chip"><Activity size={14}/> Données de votre espace</span></div>;
}

function AnalyticsKpi({ icon, label, value, detail, tone }: { icon: ReactNode; label: string; value: string; detail: string; tone: string }) {
  return <article className={`analytics-kpi-card tone-${tone}`}><span className="analytics-kpi-icon">{icon}</span><span className="analytics-kpi-label">{label}</span><b>{value}</b><small>{detail}</small></article>;
}

function NumericChart({ column }: { column: ColumnProfile }) {
  const max = Math.max(1, ...column.distribution.map((bin) => bin.count));
  if (!column.distribution.length) return <div className="analytics-no-column">Aucune valeur numérique exploitable pour ce champ.</div>;
  return <div className="numeric-chart-wrap"><div className="chart-plot" role="img" aria-label={`Distribution de ${column.name}`}><div className="chart-y-labels"><span>{max}</span><span>{Math.round(max / 2)}</span><span>0</span></div><svg viewBox={`0 0 ${Math.max(column.distribution.length * 54, 300)} 210`} preserveAspectRatio="none"><line x1="0" y1="18" x2="100%" y2="18"/><line x1="0" y1="105" x2="100%" y2="105"/><line x1="0" y1="192" x2="100%" y2="192"/>{column.distribution.map((bin, index) => { const width = Math.max(column.distribution.length * 54, 300) / column.distribution.length; const height = bin.count / max * 160; return <g key={index}><rect x={index * width + width * .2} y={192 - height} width={width * .62} height={height} rx="5"/><text x={index * width + width / 2} y="207" textAnchor="middle">{formatNumber(bin.start)}</text><title>{bin.count} valeurs de {formatNumber(bin.start)} à {formatNumber(bin.end)}</title></g>; })}</svg></div><div className="chart-legend"><span><i/> {column.name}</span><small>{column.non_null_count.toLocaleString('fr-FR')} valeurs renseignées</small></div></div>;
}

function CategoryChart({ column }: { column: ColumnProfile }) {
  const maximum = Math.max(1, ...column.category_counts.map((category) => category.count));
  if (!column.category_counts.length) return <div className="analytics-no-column">Aucune valeur textuelle exploitable pour ce champ.</div>;
  return <div className="category-chart" role="img" aria-label={`Valeurs les plus fréquentes pour ${column.name}`}>{column.category_counts.map((category) => <div className="category-bar-row" key={category.value}><span title={category.value}>{category.value || '(vide)'}</span><div className="category-bar-track"><i style={{width: `${category.count / maximum * 100}%`}}/></div><b>{category.count.toLocaleString('fr-FR')}</b></div>)}</div>;
}

function ChartStat({ label, value }: { label: string; value: string }) { return <div><small>{label}</small><b>{value}</b></div>; }
function formatNumber(value: number | null) { return value == null ? '—' : value.toLocaleString('fr-FR', { maximumFractionDigits: 2 }); }

function SavedDistribution({ analysis }: { analysis: SavedAnalysis }) {
  const profile = analysis.column_profile;
  const maxCount = Math.max(1, ...profile.distribution.map((bin) => bin.count));
  return <article className="saved-analysis-card"><div className="saved-analysis-heading"><span className="analysis-chart-icon"><BarChart3 size={17}/></span><div><h3>{analysis.title}</h3><p>{analysis.dataset_name} · {profile.name}</p></div></div><div className="saved-histogram" role="img" aria-label={`Distribution de ${profile.name} dans ${analysis.dataset_name}`}>{profile.distribution.map((bin, index) => <div className="distribution-bin" key={index} title={`${bin.count} valeur${bin.count === 1 ? '' : 's'} entre ${bin.start} et ${bin.end}`}><span style={{height: `${Math.max(5, bin.count / maxCount * 100)}px`}}/><small>{bin.count}</small></div>)}</div><div className="distribution-range"><span>{formatNumber(profile.minimum)}</span><span>{formatNumber(profile.maximum)}</span></div><div className="saved-analysis-stats"><span>Moyenne <b>{formatNumber(profile.average)}</b></span><span>{profile.non_null_count.toLocaleString('fr-FR')} valeurs</span></div><div className="saved-analysis-date">Enregistrée le {new Intl.DateTimeFormat('fr-FR',{dateStyle:'medium'}).format(new Date(analysis.created_at))}</div></article>;
}
