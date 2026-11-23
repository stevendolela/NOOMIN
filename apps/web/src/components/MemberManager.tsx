import { useEffect, useState, type FormEvent } from 'react';
import { Check, Copy, LoaderCircle, Shield, Trash2, Users, UserPlus } from 'lucide-react';
import { api } from '../lib/api';
import { Button } from './ui/button';

type Member = { user_id: string; email: string; full_name: string; role: 'owner' | 'admin' | 'member' | 'viewer'; joined_at: string };
type Invitation = { id: string; email: string; role: Member['role']; expires_at: string; created_at: string };
type CreatedInvitation = Invitation & { token: string };
type Props = { organizationId: string; currentUserId: string; canManage: boolean; role: string; onNotice: (message: string, kind: 'success' | 'error') => void };
const roleLabels = { owner: 'Propriétaire', admin: 'Administrateur', member: 'Analyste', viewer: 'Lecteur' };

export default function MemberManager({ organizationId, currentUserId, canManage, role, onNotice }: Props) {
  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState('');
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [createdLink, setCreatedLink] = useState('');
  const [copied, setCopied] = useState(false);

  async function refresh() {
    setLoading(true);
    try { const [memberData, invitationData] = await Promise.all([api<Member[]>('/members', {}, organizationId), api<Invitation[]>('/members/invitations', {}, organizationId)]); setMembers(memberData); setInvitations(invitationData); }
    catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible de charger les membres.', 'error'); }
    finally { setLoading(false); }
  }
  useEffect(() => { if (canManage) void refresh(); }, [organizationId, canManage]);
  useEffect(() => { setCreatedLink(''); setCopied(false); }, [organizationId]);

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

  async function invite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setBusyId('new-invite');
    try { const created = await api<CreatedInvitation>('/members/invitations', { method: 'POST', body: JSON.stringify({ email: form.get('email'), role: form.get('role') }) }, organizationId); const link = `${window.location.origin}/#invite=${encodeURIComponent(created.token)}`; setCreatedLink(link); setInvitations((items) => [created, ...items]); event.currentTarget.reset(); onNotice('Lien d’invitation créé. Il ne sera pas envoyé par e-mail.', 'success'); }
    catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible de créer l’invitation.', 'error'); }
    finally { setBusyId(''); }
  }

  async function revoke(invitation: Invitation) {
    setBusyId(invitation.id);
    try { await api<void>(`/members/invitations/${invitation.id}`, { method: 'DELETE' }, organizationId); setInvitations((items) => items.filter((item) => item.id !== invitation.id)); onNotice('Invitation révoquée.', 'success'); }
    catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible de révoquer l’invitation.', 'error'); }
    finally { setBusyId(''); }
  }

  return <><div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>ORGANISATION</div><h1>Accès et membres</h1><p className="subtitle">Consultez les accès et gérez les rôles des personnes déjà rattachées à cet espace.</p></div><span className="members-count"><Users size={15}/>{members.length} membre{members.length === 1 ? '' : 's'}</span></div>
    <section className="members-panel"><div className="members-panel-head"><div><h2>Membres de l’organisation</h2><p>Les modifications de rôle prennent effet immédiatement.</p></div><Shield size={19}/></div>
      {loading ? <div className="loading-panel"><LoaderCircle className="spin" size={18}/> Chargement…</div> : members.length ? <div className="members-list">{members.map((member) => { const canEditThis = canManage && (role === 'owner' || (member.role !== 'owner' && member.role !== 'admin')); return <article className="member-row" key={member.user_id}><span className="member-avatar">{member.full_name.slice(0, 1).toUpperCase()}</span><span className="member-identity"><b>{member.full_name}{member.user_id === currentUserId && <small>Vous</small>}</b><span>{member.email}</span></span>{canEditThis ? <select aria-label={`Rôle de ${member.full_name}`} value={member.role} disabled={busyId === member.user_id} onChange={(event) => void changeRole(member, event.target.value as Member['role'])}>{role === 'owner' && <><option value="owner">Propriétaire</option><option value="admin">Administrateur</option></>}<option value="member">Analyste</option><option value="viewer">Lecteur</option></select> : <span className="member-role-static">{roleLabels[member.role]}</span>}{canEditThis && member.role !== 'owner' && <Button variant="ghost" size="sm" aria-label={`Retirer ${member.full_name}`} disabled={busyId === member.user_id} onClick={() => void remove(member)}>{busyId === member.user_id ? <LoaderCircle className="spin" size={15}/> : <Trash2 size={15}/>}</Button>}</article>;})}</div> : <p className="members-empty">Aucun membre trouvé.</p>}
    </section><section className="members-panel invitation-panel"><div className="members-panel-head"><div><h2>Inviter une personne</h2><p>Créez un lien valable 7 jours. Vous devrez le transmettre vous-même.</p></div><UserPlus size={19}/></div><form className="invitation-form" onSubmit={invite}><label>Adresse e-mail<input name="email" type="email" required placeholder="nom@entreprise.fr"/></label><label>Rôle<select name="role" defaultValue="member">{role === 'owner' && <option value="admin">Administrateur</option>}<option value="member">Analyste</option><option value="viewer">Lecteur</option></select></label><Button type="submit" size="sm" className="primary-button" disabled={busyId === 'new-invite'}>{busyId === 'new-invite' ? <LoaderCircle className="spin" size={15}/> : <UserPlus size={15}/>} Créer un lien</Button></form>{createdLink && <div className="invite-link-box"><div><b>Lien prêt à transmettre</b><span>Ce lien contient un jeton secret. Copiez-le et partagez-le uniquement avec l’invité. Si vous perdez le lien, révoquez cette invitation puis recréez-la.</span></div><input readOnly value={createdLink} aria-label="Lien d’invitation"/><Button size="sm" variant="secondary" onClick={() => { void navigator.clipboard.writeText(createdLink).then(() => setCopied(true)).catch(() => onNotice('Impossible de copier automatiquement. Sélectionnez le lien et copiez-le manuellement.', 'error')); }}>{copied ? <Check size={14}/> : <Copy size={14}/>} {copied ? 'Copié' : 'Copier'}</Button></div>}{invitations.length > 0 && <div className="pending-invitations"><h3>Invitations en attente</h3>{invitations.map((invitation) => <div className="pending-invitation-row" key={invitation.id}><span><b>{invitation.email}</b><small>{roleLabels[invitation.role]} · expire le {new Intl.DateTimeFormat('fr-FR',{dateStyle:'medium'}).format(new Date(invitation.expires_at))}</small></span><Button variant="ghost" size="sm" disabled={busyId === invitation.id} aria-label={`Révoquer l’invitation de ${invitation.email}`} onClick={() => void revoke(invitation)}><Trash2 size={14}/></Button></div>)}</div>}</section>
  </>;
}
