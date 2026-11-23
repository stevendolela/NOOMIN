import { useEffect, useState, type FormEvent } from 'react';
import { ArrowRight, LoaderCircle, LockKeyhole, Users } from 'lucide-react';
import { api } from '../lib/api';
import type { Session } from '../lib/types';
import AuthScreen from './AuthScreen';
import { Button } from './ui/button';

type Details = { email: string; role: 'owner' | 'admin' | 'member' | 'viewer'; organization_name: string; expires_at: string };
const roleLabel: Record<Details['role'], string> = { owner: 'Propriétaire', admin: 'Administrateur', member: 'Analyste', viewer: 'Lecteur' };

export default function InviteAccept({ token, session, onAccepted, onLogin, onCancel }: { token: string; session: Session | null; onAccepted: (session: Session) => void; onLogin: (session: Session) => void; onCancel: () => void }) {
  const [details, setDetails] = useState<Details | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [showLogin, setShowLogin] = useState(false);

  useEffect(() => {
    let alive = true;
    api<Details>(`/invitations/${encodeURIComponent(token)}`).then((data) => { if (alive) setDetails(data); })
      .catch((err) => { if (alive) setError(err instanceof Error ? err.message : 'Cette invitation est invalide ou expirée.'); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [token]);

  async function accept(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    if (!details) return;
    setBusy(true); setError('');
    const form = event ? new FormData(event.currentTarget) : new FormData();
    try {
      const next = await api<Session>(`/invitations/${encodeURIComponent(token)}/accept`, { method: 'POST', body: JSON.stringify({ full_name: form.get('full_name') || undefined, password: form.get('password') || undefined }) });
      onAccepted(next);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Impossible d’accepter cette invitation.';
      setError(message);
      if (message.toLowerCase().includes('connectez-vous')) setShowLogin(true);
    } finally { setBusy(false); }
  }

  if (showLogin && !session) return <AuthScreen initialMode="login" onAuthenticated={(next) => { onLogin(next); setShowLogin(false); setError('Connecté. Vous pouvez maintenant rejoindre l’organisation.'); }}/>
  return <main className="invite-page"><section className="invite-card"><a className="brand invite-brand" href="/"><span className="brand-mark"><span/><span/><span/><span/></span><span>noomin</span></a><div className="invite-icon"><Users size={22}/></div><div className="eyebrow"><span className="eyebrow-line"/>INVITATION D’ORGANISATION</div><h1>Rejoindre votre équipe</h1>{loading ? <div className="loading-panel"><LoaderCircle className="spin" size={18}/> Vérification du lien…</div> : details ? <><p className="invite-description"><b>{details.organization_name}</b> vous invite à rejoindre son espace NOOMIN.</p><div className="invite-summary"><span>Adresse invitée</span><b>{details.email}</b><span>Accès prévu</span><b>{roleLabel[details.role]}</b></div>{session ? session.user.email.toLowerCase() === details.email.toLowerCase() ? <Button className="auth-submit" disabled={busy} onClick={() => void accept()}>{busy ? <LoaderCircle className="spin" size={16}/> : <ArrowRight size={16}/>} Rejoindre l’organisation</Button> : <p className="form-error" role="alert">Connecté en tant que {session.user.email}. Cette invitation est destinée à {details.email}.</p> : <form className="invite-form" onSubmit={(event) => void accept(event)}><label>Votre nom<input name="full_name" autoComplete="name" minLength={2} maxLength={160} required placeholder="Prénom Nom"/></label><label>Créer un mot de passe<span className="invite-input-hint">12 caractères minimum</span><input name="password" type="password" autoComplete="new-password" minLength={12} maxLength={128} required placeholder="12 caractères minimum"/></label><p className="invite-email-lock"><LockKeyhole size={13}/> Le compte sera créé avec {details.email}</p><Button type="submit" className="auth-submit" disabled={busy}>{busy ? <LoaderCircle className="spin" size={16}/> : <ArrowRight size={16}/>} Accepter et créer mon compte</Button><button className="invite-login-link" type="button" onClick={() => setShowLogin(true)}>J’ai déjà un compte NOOMIN</button></form>}{error && <div className="form-error" role="alert">{error}</div>}</> : <div className="form-error" role="alert">{error || 'Cette invitation est invalide ou a expiré.'}</div>}<button className="invite-cancel" onClick={onCancel}>Retour à NOOMIN</button><p className="invite-footnote">Les invitations sont transmises par lien ; aucun e-mail n’est envoyé par NOOMIN pour le moment.</p></section></main>;
}
