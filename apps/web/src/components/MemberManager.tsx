import { useEffect, useState } from 'react';
import { LoaderCircle, Shield, Trash2, Users } from 'lucide-react';
import { api } from '../lib/api';
import { Button } from './ui/button';

type Member = { user_id: string; email: string; full_name: string; role: 'owner' | 'admin' | 'member' | 'viewer'; joined_at: string };
type Props = { organizationId: string; currentUserId: string; canManage: boolean; role: string; onNotice: (message: string, kind: 'success' | 'error') => void };
const roleLabels = { owner: 'Propriétaire', admin: 'Administrateur', member: 'Analyste', viewer: 'Lecteur' };

export default function MemberManager({ organizationId, currentUserId, canManage, role, onNotice }: Props) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState('');

  async function refresh() {
    setLoading(true);
    try { setMembers(await api<Member[]>('/members', {}, organizationId)); }
    catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible de charger les membres.', 'error'); }
    finally { setLoading(false); }
  }
  useEffect(() => { if (canManage) void refresh(); }, [organizationId, canManage]);

  if (!canManage) return <><div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>ORGANISATION</div><h1>Accès et membres</h1><p className="subtitle">La gestion des membres est réservée aux administrateurs et propriétaires.</p></div></div></>;

  async function changeRole(member: Member, nextRole: Member['role']) {
    setBusyId(member.user_id);
    try { const updated = await api<Member>(`/members/${member.user_id}`, { method: 'PATCH', body: JSON.stringify({ role: nextRole }) }, organizationId); setMembers((items) => items.map((item) => item.user_id === updated.user_id ? updated : item)); onNotice('Rôle mis à jour.', 'success'); }
    catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible de modifier ce rôle.', 'error'); }
    finally { setBusyId(''); }
  }

  async function remove(member: Member) {
    if (!window.confirm(`Retirer ${member.full_name} de cette organisation ?`)) return;
    setBusyId(member.user_id);
    try { await api<void>(`/members/${member.user_id}`, { method: 'DELETE' }, organizationId); setMembers((items) => items.filter((item) => item.user_id !== member.user_id)); onNotice('Membre retiré de l’organisation.', 'success'); }
    catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible de retirer ce membre.', 'error'); }
    finally { setBusyId(''); }
  }

  return <><div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>ORGANISATION</div><h1>Accès et membres</h1><p className="subtitle">Consultez les accès et gérez les rôles des personnes déjà rattachées à cet espace.</p></div><span className="members-count"><Users size={15}/>{members.length} membre{members.length === 1 ? '' : 's'}</span></div>
    <section className="members-panel"><div className="members-panel-head"><div><h2>Membres de l’organisation</h2><p>Les modifications de rôle prennent effet immédiatement.</p></div><Shield size={19}/></div>
      {loading ? <div className="loading-panel"><LoaderCircle className="spin" size={18}/> Chargement…</div> : members.length ? <div className="members-list">{members.map((member) => { const canEditThis = canManage && (role === 'owner' || (member.role !== 'owner' && member.role !== 'admin')); return <article className="member-row" key={member.user_id}><span className="member-avatar">{member.full_name.slice(0, 1).toUpperCase()}</span><span className="member-identity"><b>{member.full_name}{member.user_id === currentUserId && <small>Vous</small>}</b><span>{member.email}</span></span>{canEditThis ? <select aria-label={`Rôle de ${member.full_name}`} value={member.role} disabled={busyId === member.user_id} onChange={(event) => void changeRole(member, event.target.value as Member['role'])}>{role === 'owner' && <><option value="owner">Propriétaire</option><option value="admin">Administrateur</option></>}<option value="member">Analyste</option><option value="viewer">Lecteur</option></select> : <span className="member-role-static">{roleLabels[member.role]}</span>}{canEditThis && member.role !== 'owner' && <Button variant="ghost" size="sm" aria-label={`Retirer ${member.full_name}`} disabled={busyId === member.user_id} onClick={() => void remove(member)}>{busyId === member.user_id ? <LoaderCircle className="spin" size={15}/> : <Trash2 size={15}/>}</Button>}</article>;})}</div> : <p className="members-empty">Aucun membre trouvé.</p>}
    </section><div className="members-invite-note"><b>Invitations non activées</b><span>L’ajout de membres par invitation e-mail nécessite encore une fonctionnalité dédiée.</span></div>
  </>;
}
