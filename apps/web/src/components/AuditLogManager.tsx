import { useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, ClipboardList, LoaderCircle } from 'lucide-react';
import { api } from '../lib/api';
import { Button } from './ui/button';

type AuditEvent = { id: string; actor_name: string; actor_email: string | null; action: string; entity_type: string; entity_id: string | null; metadata: Record<string, string | number | boolean>; created_at: string };
type AuditPage = { items: AuditEvent[]; total: number };
const actionLabels: Record<string, string> = {
  'organization.created': 'Organisation créée', 'dataset.imported': 'Jeu de données importé', 'dataset.deleted': 'Jeu de données supprimé',
  'analysis.saved': 'Analyse enregistrée', 'pipeline.created': 'Pipeline créé', 'pipeline.run_requested': 'Exécution lancée',
  'member.role_changed': 'Rôle modifié', 'member.removed': 'Membre retiré', 'invitation.created': 'Invitation créée',
  'invitation.revoked': 'Invitation révoquée', 'invitation.accepted': 'Invitation acceptée',
};

function details(event: AuditEvent) {
  const values = event.metadata;
  const parts: string[] = [];
  if (typeof values.new_role === 'string') parts.push(`${values.previous_role ?? '—'} → ${values.new_role}`);
  if (typeof values.role === 'string') parts.push(`Rôle : ${values.role}`);
  if (typeof values.row_count === 'number') parts.push(`${values.row_count.toLocaleString('fr-FR')} lignes`);
  if (typeof values.column_count === 'number') parts.push(`${values.column_count} colonnes`);
  if (typeof values.step_count === 'number') parts.push(`${values.step_count} étapes`);
  return parts.join(' · ');
}

export default function AuditLogManager({ organizationId, onNotice }: { organizationId: string; onNotice: (message: string, kind: 'success' | 'error') => void }) {
  const [page, setPage] = useState(0);
  const [data, setData] = useState<AuditPage>({ items: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const pageSize = 30;

  useEffect(() => {
    let alive = true;
    setLoading(true);
    api<AuditPage>(`/audit?limit=${pageSize}&offset=${page * pageSize}`, {}, organizationId)
      .then((result) => { if (alive) setData(result); })
      .catch((error) => { if (alive) onNotice(error instanceof Error ? error.message : 'Impossible de charger le journal.', 'error'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [organizationId, page]);

  useEffect(() => { setPage(0); }, [organizationId]);
  const pageCount = Math.max(1, Math.ceil(data.total / pageSize));
  return <><div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>TRAÇABILITÉ</div><h1>Journal d’audit</h1><p className="subtitle">Actions importantes enregistrées dans l’organisation, sans contenu de fichiers ni secrets.</p></div><span className="members-count"><ClipboardList size={15}/>{data.total} événements</span></div>
    <section className="audit-panel">{loading ? <div className="loading-panel"><LoaderCircle size={18} className="spin"/> Chargement…</div> : data.items.length ? <div className="audit-list">{data.items.map((event) => <article className="audit-event" key={event.id}><span className="audit-event-mark"><ClipboardList size={15}/></span><div className="audit-event-copy"><b>{actionLabels[event.action] ?? event.action}</b><span>{event.actor_name}{event.actor_email ? ` · ${event.actor_email}` : ''}</span>{details(event) && <small>{details(event)}</small>}</div><time dateTime={event.created_at}>{new Intl.DateTimeFormat('fr-FR',{dateStyle:'medium',timeStyle:'short'}).format(new Date(event.created_at))}</time></article>)}</div> : <div className="pipeline-empty"><div className="empty-icon"><ClipboardList size={20}/></div><h3>Aucune activité enregistrée</h3><p>Les actions de l’organisation apparaîtront ici.</p></div>}
      <div className="audit-pagination"><span>{data.total ? `${page + 1} / ${pageCount}` : '—'}</span><div><Button size="sm" variant="secondary" disabled={page === 0 || loading} onClick={() => setPage((value) => Math.max(0, value - 1))}><ArrowLeft size={14}/> Précédent</Button><Button size="sm" variant="secondary" disabled={page + 1 >= pageCount || loading} onClick={() => setPage((value) => value + 1)}>Suivant <ArrowRight size={14}/></Button></div></div>
    </section><p className="audit-retention-note">Les journaux n’incluent pas les valeurs CSV, mots de passe, jetons ou liens d’invitation.</p>
  </>;
}
