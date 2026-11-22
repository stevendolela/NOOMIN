import { useState, type FormEvent } from 'react';
import { Activity, ArrowRight, Database, Eye, EyeOff, LockKeyhole, Sparkles } from 'lucide-react';
import { Button } from './ui/button';
import { api } from '../lib/api';
import type { Session } from '../lib/types';

export default function AuthScreen({ onAuthenticated }: { onAuthenticated: (session: Session) => void }) {
  const [mode, setMode] = useState<'login' | 'register'>('register');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(''); setBusy(true);
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    try {
      const session = await api<Session>(`/auth/${mode}`, { method: 'POST', body: JSON.stringify(payload) });
      onAuthenticated(session);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connexion impossible.');
    } finally { setBusy(false); }
  }

  return <main className="auth-page">
    <section className="auth-story">
      <a className="brand auth-brand" href="#home"><span className="brand-mark"><span/><span/><span/><span/></span><span>noomin</span></a>
      <div className="story-content"><div className="welcome-badge"><Sparkles size={14}/> LA DATA AU SERVICE DE VOS DÉCISIONS</div><h1>Voyez clair.<br/><span>Décidez mieux.</span></h1><p>Un espace unique pour rassembler vos données, explorer votre activité et construire vos analyses.</p><div className="story-orbit"><div className="story-ring ring-a"/><div className="story-ring ring-b"/><div className="story-ring ring-c"/><div className="story-core"><span className="brand-mark large"><span/><span/><span/><span/></span></div><div className="story-node story-node-a"><Database size={17}/></div><div className="story-node story-node-b"><Activity size={17}/></div><div className="story-node story-node-c"><Sparkles size={17}/></div></div><div className="story-points"><span><i/>Importez vos données en toute simplicité</span><span><i/>Gardez chaque organisation isolée</span></div></div>
      <div className="auth-story-footer">© 2026 NOOMIN <span>·</span> L’intelligence en mouvement</div>
    </section>
    <section className="auth-form-side"><div className="auth-mobile-brand"><span className="brand-mark"><span/><span/><span/><span/></span> noomin</div><div className="auth-card"><div className="auth-kicker">VOTRE ESPACE DE PILOTAGE</div><h2>{mode === 'register' ? 'Commencez ici.' : 'Content de vous revoir.'}</h2><p className="auth-subtitle">{mode === 'register' ? 'Créez votre espace NOOMIN en quelques instants.' : 'Connectez-vous à votre espace de travail.'}</p><div className="auth-tabs"><button className={mode === 'register' ? 'active' : ''} onClick={() => { setMode('register'); setError(''); }}>Créer un compte</button><button className={mode === 'login' ? 'active' : ''} onClick={() => { setMode('login'); setError(''); }}>Se connecter</button></div>
      <form onSubmit={submit} className="auth-fields">{mode === 'register' && <><label>Votre nom<input name="full_name" autoComplete="name" placeholder="Camille Martin" required minLength={2} maxLength={160}/></label><label>Nom de votre organisation<input name="organization_name" autoComplete="organization" placeholder="Acme Studio" required minLength={2} maxLength={160}/></label></>}<label>Adresse e-mail<input name="email" type="email" autoComplete="email" placeholder="vous@entreprise.fr" required/></label><label>Mot de passe<span className="password-input"><input name="password" type={showPassword ? 'text' : 'password'} autoComplete={mode === 'register' ? 'new-password' : 'current-password'} placeholder={mode === 'register' ? '12 caractères minimum' : 'Votre mot de passe'} required minLength={mode === 'register' ? 12 : 1} maxLength={128}/><button type="button" aria-label={showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={16}/> : <Eye size={16}/>}</button></span></label>
      {error && <div className="form-error" role="alert">{error}</div>}<Button type="submit" className="auth-submit" disabled={busy}>{busy ? 'Un instant…' : mode === 'register' ? 'Créer mon espace' : 'Se connecter'}{!busy && <ArrowRight size={16}/>}</Button></form><div className="auth-security"><LockKeyhole size={14}/><span>Connexion sécurisée · données isolées par organisation</span></div><p className="auth-terms">En continuant, vous créez un compte de développement NOOMIN. La vérification de l’adresse e-mail n’est pas encore activée.</p></div><div className="auth-form-footer">Une question ? <span>Le centre d’aide sera disponible prochainement.</span></div></section>
  </main>;
}
