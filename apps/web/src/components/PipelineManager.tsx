import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { Activity, ArrowRight, Check, ChevronDown, ChevronRight, CircleAlert, Clock3, Columns3, LoaderCircle, Play, Plus, Workflow } from 'lucide-react';
import { api } from '../lib/api';
import { Button } from './ui/button';
import type { Dataset, Pipeline, PipelineRunHistory } from '../lib/types';

type Props = { organizationId: string; datasets: Dataset[]; canEdit: boolean; onOutput: () => Promise<void>; onNotice: (message: string, kind: 'success' | 'error') => void };

export default function PipelineManager({ organizationId, datasets, canEdit, onOutput, onNotice }: Props) {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [runningId, setRunningId] = useState('');
  const [sourceId, setSourceId] = useState('');
  const [name, setName] = useState('');
  const [selectedColumns, setSelectedColumns] = useState<string[]>([]);
  const [filterColumn, setFilterColumn] = useState('');
  const [operator, setOperator] = useState('equals');
  const [filterValue, setFilterValue] = useState('');
  const [history, setHistory] = useState<Record<string, PipelineRunHistory>>({});
  const [historyLoading, setHistoryLoading] = useState<Record<string, boolean>>({});
  const [historyOpen, setHistoryOpen] = useState<Record<string, boolean>>({});
  const source = datasets.find((dataset) => dataset.id === sourceId);

  async function refresh() { setLoading(true); try { setPipelines(await api<Pipeline[]>('/pipelines', {}, organizationId)); } catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible de charger les pipelines.', 'error'); } finally { setLoading(false); } }
  useEffect(() => { void refresh(); }, [organizationId]);
  useEffect(() => { if (!sourceId && datasets.length) setSourceId(datasets[0].id); }, [datasets, sourceId]);
  useEffect(() => { if (source) { setSelectedColumns(source.columns); setFilterColumn(''); setFilterValue(''); } }, [sourceId]);

  const canFilterValue = operator !== 'is_empty' && operator !== 'is_not_empty';
  const transformationsCount = 1 + (filterColumn ? 1 : 0);
  const latestRun = (pipeline: Pipeline) => pipeline.last_run;

  async function loadHistory(pipelineId: string) {
    setHistoryLoading((items) => ({ ...items, [pipelineId]: true }));
    try { const result = await api<PipelineRunHistory>(`/pipelines/${pipelineId}/runs?limit=20`, {}, organizationId); setHistory((items) => ({ ...items, [pipelineId]: result })); }
    catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible de charger l’historique.', 'error'); }
    finally { setHistoryLoading((items) => ({ ...items, [pipelineId]: false })); }
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!source || selectedColumns.length === 0) return;
    setSaving(true);
    try {
      const steps: Array<Record<string, unknown>> = [];
      if (filterColumn) steps.push({ op: 'filter_rows', column: filterColumn, operator, value: canFilterValue ? filterValue : null });
      steps.push({ op: 'select_columns', columns: selectedColumns });
      await api<Pipeline>('/pipelines', { method: 'POST', body: JSON.stringify({ name, source_dataset_id: sourceId, steps }) }, organizationId);
      setName(''); await refresh(); onNotice('Pipeline enregistré. Vous pouvez le lancer quand vous le souhaitez.', 'success');
    } catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible d’enregistrer le pipeline.', 'error'); }
    finally { setSaving(false); }
  }

  async function run(pipeline: Pipeline) {
    setRunningId(pipeline.id);
    try {
      await api(`/pipelines/${pipeline.id}/runs`, { method: 'POST' }, organizationId);
      let current: Pipeline | undefined;
      for (let attempt = 0; attempt < 40; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
        current = await api<Pipeline>(`/pipelines/${pipeline.id}`, {}, organizationId);
        setPipelines((items) => items.map((item) => item.id === pipeline.id ? current! : item));
        if (current.last_run?.status === 'succeeded') { onNotice(`Pipeline terminé : ${current.last_run.output_dataset_id ? 'un nouveau jeu de données a été créé.' : 'aucune sortie disponible.'}`, 'success'); await onOutput(); return; }
        if (current.last_run?.status === 'failed') { onNotice(current.last_run.error_message ?? 'Le pipeline a échoué.', 'error'); return; }
      }
      onNotice('Le traitement est toujours en file d’attente. Vous pouvez revenir consulter son statut.', 'success');
    } catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible de lancer le pipeline.', 'error'); }
    finally { setRunningId(''); }
  }

  const runLabel = useMemo(() => (status: string) => status === 'succeeded' ? 'Terminé' : status === 'failed' ? 'Échec' : status === 'running' ? 'En cours' : 'En attente', []);
  const formatRunDate = (value: string) => new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));

  return <>
    <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>TRANSFORMATIONS DE DONNÉES</div><h1>Pipelines</h1><p className="subtitle">Sélectionnez, filtrez et transformez les jeux de données de cette organisation.</p></div><span className="pipeline-queue-chip"><i/> Exécution asynchrone</span></div>
    {!datasets.length ? <div className="empty-datasets"><div className="empty-icon"><Workflow size={21}/></div><h3>Importez d’abord un jeu de données</h3><p>Les pipelines transforment les fichiers CSV déjà importés dans votre espace.</p></div> : <div className="pipeline-layout">
      {canEdit && <section className="pipeline-builder"><div className="builder-heading"><span className="builder-icon"><Plus size={17}/></span><div><h2>Nouveau pipeline</h2><p>Définissez les étapes à exécuter sur votre source.</p></div></div><form onSubmit={create} className="builder-form"><label>Nom du pipeline<input value={name} onChange={(event) => setName(event.target.value)} placeholder="Ex. Ventes filtrées" minLength={2} maxLength={160} required/></label><label>Jeu de données source<select value={sourceId} onChange={(event) => setSourceId(event.target.value)}>{datasets.map((dataset) => <option key={dataset.id} value={dataset.id}>{dataset.name} · {dataset.row_count.toLocaleString('fr-FR')} lignes</option>)}</select></label>
        {source && <><div className="builder-subhead"><Columns3 size={15}/><b>Colonnes conservées</b><small>{selectedColumns.length} / {source.columns.length}</small></div><div className="column-picker">{source.columns.map((column) => <label key={column} className="column-option"><input type="checkbox" checked={selectedColumns.includes(column)} onChange={(event) => setSelectedColumns((items) => event.target.checked ? [...items, column] : items.filter((item) => item !== column))}/><span>{column}</span></label>)}</div><details className="filter-details"><summary><Activity size={14}/> Ajouter un filtre facultatif</summary><div className="filter-fields"><label>Colonne<select value={filterColumn} onChange={(event) => setFilterColumn(event.target.value)}><option value="">Aucun filtre</option>{source.columns.map((column) => <option key={column}>{column}</option>)}</select></label>{filterColumn && <><label>Condition<select value={operator} onChange={(event) => setOperator(event.target.value)}><option value="equals">est égal à</option><option value="not_equals">est différent de</option><option value="contains">contient</option><option value="greater_than">est supérieur à</option><option value="less_than">est inférieur à</option><option value="is_empty">est vide</option><option value="is_not_empty">n’est pas vide</option></select></label>{canFilterValue && <label>Valeur<input value={filterValue} onChange={(event) => setFilterValue(event.target.value)} maxLength={500} required placeholder="Valeur de comparaison"/></label>}</>}</div></details></>}
        <div className="builder-summary"><span><Check size={14}/> {transformationsCount} étape{transformationsCount > 1 ? 's' : ''}</span><span><Clock3 size={14}/> Traitement en arrière-plan</span></div><Button type="submit" size="sm" className="primary-button builder-submit" disabled={saving || !name.trim() || !selectedColumns.length}>{saving ? <LoaderCircle className="spin" size={16}/> : <Plus size={16}/>} Enregistrer le pipeline</Button></form></section>}
      <section className="pipeline-list"><div className="pipeline-list-heading"><div><h2>Vos pipelines</h2><p>{pipelines.length} pipeline{pipelines.length === 1 ? '' : 's'} enregistré{pipelines.length === 1 ? '' : 's'}</p></div></div>{loading ? <div className="loading-panel"><LoaderCircle className="spin" size={18}/> Chargement…</div> : pipelines.length ? <div className="pipeline-cards">{pipelines.map((pipeline) => { const runData = latestRun(pipeline); const runs = history[pipeline.id]; const isOpen = historyOpen[pipeline.id]; return <article className="pipeline-card" key={pipeline.id}><div className="pipeline-card-top"><span className="pipeline-card-icon"><Workflow size={17}/></span><div className="pipeline-card-title"><h3>{pipeline.name}</h3><p>Source : {pipeline.source_dataset_name}</p></div>{runData && <span className={`run-status status-${runData.status}`}>{runData.status === 'running' && <LoaderCircle className="spin" size={11}/>} {runLabel(runData.status)}</span>}</div><div className="pipeline-steps-display"><span>{pipeline.steps.length} étape{pipeline.steps.length > 1 ? 's' : ''}</span><ChevronRight size={13}/><span>Sortie : nouveau jeu de données</span></div>{runData?.error_message && <p className="run-error"><CircleAlert size={13}/>{runData.error_message}</p>}{runData?.output_dataset_id && runData.status === 'succeeded' && <p className="run-output"><Check size={13}/> Résultat créé dans vos jeux de données</p>}<div className="pipeline-card-footer"><span>Créé le {new Intl.DateTimeFormat('fr-FR',{dateStyle:'medium'}).format(new Date(pipeline.created_at))}</span>{canEdit && <Button size="sm" variant="secondary" disabled={runningId === pipeline.id || runData?.status === 'running' || runData?.status === 'queued'} onClick={() => void run(pipeline)}>{runningId === pipeline.id ? <LoaderCircle className="spin" size={14}/> : <Play size={14}/>} Lancer</Button>}</div><button className="run-history-toggle" aria-expanded={Boolean(isOpen)} onClick={() => { const next = !isOpen; setHistoryOpen((items) => ({ ...items, [pipeline.id]: next })); if (next && !runs) void loadHistory(pipeline.id); }}><span><Clock3 size={13}/> Historique des exécutions{runs ? ` · ${runs.total}` : ''}</span>{historyLoading[pipeline.id] ? <LoaderCircle className="spin" size={14}/> : <ChevronDown size={14}/>}</button>{isOpen && <div className="run-history-list">{historyLoading[pipeline.id] && !runs ? <div className="run-history-empty">Chargement de l’historique…</div> : runs?.items.length ? runs.items.map((item) => <div className="run-history-item" key={item.id}><span className={`run-status status-${item.status}`}>{runLabel(item.status)}</span><span className="run-history-date">{formatRunDate(item.created_at)}</span>{item.finished_at && <span className="run-history-duration">{Math.max(0, Math.round((new Date(item.finished_at).getTime() - new Date(item.started_at ?? item.created_at).getTime()) / 1000))} s</span>}{item.error_message && <p className="run-history-error"><CircleAlert size={12}/>{item.error_message}</p>}</div>) : <div className="run-history-empty">Aucune exécution enregistrée.</div>}</div>}</article>;})}</div> : <div className="pipeline-empty"><div className="empty-icon"><Workflow size={20}/></div><h3>Pas encore de pipeline</h3><p>Créez une transformation à partir de votre CSV.</p></div>}</section>
    </div>}
    <div className="pipeline-capability-note"><ArrowRight size={14}/> Les étapes disponibles sont la sélection de colonnes, le filtrage et l’exécution vers un nouveau jeu de données.</div>
  </>;
}
