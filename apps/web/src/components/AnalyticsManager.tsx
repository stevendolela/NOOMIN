import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Activity, BarChart3, Check, LoaderCircle, Plus, Sparkles } from 'lucide-react';
import { api } from '../lib/api';
import { Button } from './ui/button';
import type { Dataset, DatasetProfile, SavedAnalysis } from '../lib/types';

type Props = { organizationId: string; datasets: Dataset[]; canEdit: boolean; onNotice: (message: string, kind: 'success' | 'error') => void };

export default function AnalyticsManager({ organizationId, datasets, canEdit, onNotice }: Props) {
  const [analyses, setAnalyses] = useState<SavedAnalysis[]>([]);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [datasetId, setDatasetId] = useState('');
  const [columnName, setColumnName] = useState('');
  const [title, setTitle] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const numericColumns = useMemo(() => profile?.columns.filter((column) => column.data_type === 'number') ?? [], [profile]);

  async function loadAnalyses() { setLoading(true); try { setAnalyses(await api<SavedAnalysis[]>('/analyses', {}, organizationId)); } catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible de charger les analyses.', 'error'); } finally { setLoading(false); } }
  useEffect(() => { void loadAnalyses(); }, [organizationId]);
  useEffect(() => { if (!datasetId && datasets.length) setDatasetId(datasets[0].id); }, [datasets, datasetId]);
  useEffect(() => {
    if (!datasetId) { setProfile(null); setColumnName(''); return; }
    let alive = true; setProfile(null); setColumnName('');
    api<DatasetProfile>(`/datasets/${datasetId}/profile`, {}, organizationId).then((value) => {
      if (alive) { setProfile(value); setColumnName(value.columns.find((column) => column.data_type === 'number')?.name ?? ''); }
    }).catch((error) => { if (alive) onNotice(error instanceof Error ? error.message : 'Impossible de profiler ce jeu de données.', 'error'); });
    return () => { alive = false; };
  }, [datasetId, organizationId]);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!datasetId || !columnName) return;
    setSaving(true);
    try {
      await api<SavedAnalysis>('/analyses', { method: 'POST', body: JSON.stringify({ title: title.trim() || `Distribution de ${columnName}`, dataset_id: datasetId, column_name: columnName }) }, organizationId);
      setTitle(''); await loadAnalyses(); onNotice('Distribution enregistrée à partir des données importées.', 'success');
    } catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible d’enregistrer cette analyse.', 'error'); }
    finally { setSaving(false); }
  }

  return <>
    <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>EXPLORATION DE VOS DONNÉES</div><h1>Analyses</h1><p className="subtitle">Enregistrez les distributions numériques de vos jeux de données.</p></div><span className="analysis-source-chip"><Activity size={14}/> Calculs issus de vos imports</span></div>
    {!datasets.length ? <div className="empty-datasets"><div className="empty-icon"><BarChart3 size={21}/></div><h3>Importez un jeu de données pour commencer</h3><p>Vous pourrez enregistrer des distributions à partir des colonnes numériques détectées.</p></div> : <div className="analytics-layout">
      {canEdit && <section className="analysis-builder"><div className="builder-heading"><span className="builder-icon"><Sparkles size={17}/></span><div><h2>Nouvelle distribution</h2><p>Le graphique sera calculé à partir des lignes importées.</p></div></div><form onSubmit={save} className="builder-form"><label>Nom de l’analyse<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Ex. Distribution des coûts" maxLength={160}/></label><label>Jeu de données<select value={datasetId} onChange={(event) => setDatasetId(event.target.value)}>{datasets.map((dataset) => <option value={dataset.id} key={dataset.id}>{dataset.name}</option>)}</select></label><label>Colonne numérique<select value={columnName} onChange={(event) => setColumnName(event.target.value)} disabled={!numericColumns.length}>{numericColumns.length ? numericColumns.map((column) => <option value={column.name} key={column.name}>{column.name}</option>) : <option value="">Aucune colonne numérique</option>}</select></label>{numericColumns.length ? <div className="analysis-preview-note"><Check size={14}/><span>{profile?.row_count.toLocaleString('fr-FR')} lignes incluses · distribution en classes calculée à l’enregistrement</span></div> : <div className="analysis-empty-note">{profile ? 'Ce jeu ne contient pas de colonne numérique exploitable.' : 'Détection des colonnes…'}</div>}<Button size="sm" className="primary-button builder-submit" disabled={saving || !columnName}>{saving ? <LoaderCircle size={15} className="spin"/> : <Plus size={15}/>} Enregistrer l’analyse</Button></form></section>}
      <section className="saved-analyses"><div className="pipeline-list-heading"><div><h2>Analyses enregistrées</h2><p>{analyses.length} distribution{analyses.length === 1 ? '' : 's'} sauvegardée{analyses.length === 1 ? '' : 's'} dans cette organisation.</p></div></div>{loading ? <div className="loading-panel"><LoaderCircle size={18} className="spin"/> Chargement…</div> : analyses.length ? <div className="saved-analysis-grid">{analyses.map((analysis) => <SavedDistribution key={analysis.id} analysis={analysis}/>)}</div> : <div className="pipeline-empty"><div className="empty-icon"><BarChart3 size={20}/></div><h3>Aucune analyse enregistrée</h3><p>Choisissez une colonne numérique pour créer la première.</p></div>}</section>
    </div>}
    <div className="pipeline-capability-note"><Activity size={14}/> Les distributions enregistrées sont des résumés descriptifs des CSV importés ; aucun modèle IA n’est activé.</div>
  </>;
}

function SavedDistribution({ analysis }: { analysis: SavedAnalysis }) {
  const profile = analysis.column_profile;
  const maxCount = Math.max(1, ...profile.distribution.map((bin) => bin.count));
  return <article className="saved-analysis-card"><div className="saved-analysis-heading"><span className="analysis-chart-icon"><BarChart3 size={17}/></span><div><h3>{analysis.title}</h3><p>{analysis.dataset_name} · {profile.name}</p></div></div><div className="saved-histogram" role="img" aria-label={`Distribution de ${profile.name} dans ${analysis.dataset_name}`}>{profile.distribution.map((bin, index) => <div className="distribution-bin" key={index} title={`${bin.count} valeur${bin.count === 1 ? '' : 's'} entre ${bin.start} et ${bin.end}`}><span style={{height: `${Math.max(5, bin.count / maxCount * 100)}px`}}/><small>{bin.count}</small></div>)}</div><div className="distribution-range"><span>{profile.minimum?.toLocaleString('fr-FR')}</span><span>{profile.maximum?.toLocaleString('fr-FR')}</span></div><div className="saved-analysis-stats"><span>Moyenne <b>{profile.average?.toLocaleString('fr-FR',{maximumFractionDigits:2})}</b></span><span>{profile.non_null_count.toLocaleString('fr-FR')} valeurs</span></div><div className="saved-analysis-date">Enregistrée le {new Intl.DateTimeFormat('fr-FR',{dateStyle:'medium'}).format(new Date(analysis.created_at))}</div></article>;
}
