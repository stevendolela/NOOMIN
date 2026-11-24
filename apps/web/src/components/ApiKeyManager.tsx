import { useEffect, useState, type FormEvent } from 'react';
import { AlertTriangle, Check, Copy, KeyRound, LoaderCircle, Plus, Trash2 } from 'lucide-react';
import { api } from '../lib/api';
import { Button } from './ui/button';

type APIKey = { id: string; name: string; key_prefix: string; scopes: string[]; created_at: string; expires_at: string | null; last_used_at: string | null; revoked_at: string | null };
type CreatedAPIKey = APIKey & { secret: string };
type Props = { organizationId: string; onNotice: (message: string, kind: 'success' | 'error') => void };
const scopeLabels: Record<string, string> = { 'datasets:read': 'Lire les jeux de données et les lignes', 'profiles:read': 'Lire les profils de colonnes' };
const date = (value: string | null) => value ? new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : 'Jamais';
const expired = (key: APIKey) => Boolean(key.expires_at && new Date(key.expires_at).getTime() <= Date.now());

export default function ApiKeyManager({ organizationId, onNotice }: Props) {
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [createdKey, setCreatedKey] = useState<CreatedAPIKey | null>(null);
  const [copied, setCopied] = useState(false);

  async function refresh() {
    setLoading(true);
    try { setKeys(await api<APIKey[]>('/api-keys', {}, organizationId)); }
    catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible de charger les clés API.', 'error'); }
    finally { setLoading(false); }
  }
  useEffect(() => { setCreatedKey(null); setCopied(false); void refresh(); }, [organizationId]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const scopes = ['datasets:read', ...(form.get('profiles') === 'on' ? ['profiles:read'] : [])];
    setBusy(true);
    try {
      const result = await api<CreatedAPIKey>('/api-keys', { method: 'POST', body: JSON.stringify({ name: form.get('name'), scopes, expires_in_days: Number(form.get('expiry')) }) }, organizationId);
      setCreatedKey(result); setCopied(false); formElement.reset(); await refresh();
      onNotice('Clé API créée. Copiez-la maintenant : elle ne sera plus affichée ensuite.', 'success');
    } catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible de créer la clé API.', 'error'); }
    finally { setBusy(false); }
  }

  async function revoke(key: APIKey) {
    if (!window.confirm(`Révoquer la clé « ${key.name} » ? Les applications qui l’utilisent perdront l’accès immédiatement.`)) return;
    setBusy(true);
    try { await api<void>(`/api-keys/${key.id}`, { method: 'DELETE' }, organizationId); await refresh(); onNotice('Clé API révoquée.', 'success'); }
    catch (error) { onNotice(error instanceof Error ? error.message : 'Impossible de révoquer la clé.', 'error'); }
    finally { setBusy(false); }
  }

  return <>
    <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>INTÉGRATIONS</div><h1>Accès API</h1><p className="subtitle">Créez une clé de lecture pour connecter une application aux données de cette organisation.</p></div><span className="members-count"><KeyRound size={15}/>{keys.filter((key) => !key.revoked_at && !expired(key)).length} clé(s) active(s)</span></div>
    <section className="members-panel"><div className="members-panel-head"><div><h2>Créer une clé API</h2><p>Chaque clé est liée à cet espace de travail et ne peut lire que ses données.</p></div><KeyRound size={19}/></div>
      <form className="api-key-form" onSubmit={(event) => void create(event)}><label>Nom de la clé<input name="name" required minLength={2} maxLength={100} placeholder="Ex. Reporting interne"/></label><label>Expiration<select name="expiry" defaultValue="90"><option value="30">30 jours</option><option value="90">90 jours</option><option value="180">180 jours</option><option value="365">1 an</option></select></label><label className="api-key-scope"><input name="profiles" type="checkbox" defaultChecked/> Autoriser la lecture des profils</label><Button type="submit" size="sm" className="primary-button" disabled={busy}>{busy ? <LoaderCircle className="spin" size={15}/> : <Plus size={15}/>} Créer une clé</Button></form>
      {createdKey && <div className="api-key-secret"><div><b><AlertTriangle size={14}/> Copiez cette clé maintenant</b><span>NOOMIN ne conserve que son empreinte. Après avoir quitté cette page, la valeur complète ne pourra plus être récupérée.</span></div><code>{createdKey.secret}</code><Button size="sm" variant="secondary" onClick={() => { void navigator.clipboard.writeText(createdKey.secret).then(() => setCopied(true)).catch(() => onNotice('Copie automatique impossible. Sélectionnez la clé et copiez-la manuellement.', 'error')); }}>{copied ? <Check size={14}/> : <Copy size={14}/>} {copied ? 'Copiée' : 'Copier'}</Button></div>}
    </section>
    <section className="members-panel api-keys-panel"><div className="members-panel-head"><div><h2>Clés de cette organisation</h2><p>Révoquez immédiatement toute clé qui n’est plus utilisée.</p></div><KeyRound size={19}/></div>
      {loading ? <div className="loading-panel"><LoaderCircle className="spin" size={18}/> Chargement…</div> : keys.length ? <div className="api-keys-list">{keys.map((key) => { const isExpired = expired(key); return <article className="api-key-row" key={key.id}><span className={`api-key-status ${key.revoked_at || isExpired ? 'revoked' : ''}`}/><div className="api-key-info"><b>{key.name}{key.revoked_at && <small>Révoquée</small>}{!key.revoked_at && isExpired && <small>Expirée</small>}</b><code>{key.key_prefix}…</code><span>{key.scopes.map((scope) => scopeLabels[scope] ?? scope).join(' · ')}</span><small>Créée le {date(key.created_at)} · Expire {key.expires_at ? `le ${date(key.expires_at)}` : 'jamais'} · Dernier usage : {date(key.last_used_at)}</small></div>{!key.revoked_at && <Button variant="ghost" size="sm" aria-label={`Révoquer ${key.name}`} disabled={busy} onClick={() => void revoke(key)}><Trash2 size={15}/></Button>}</article>;})}</div> : <div className="pipeline-empty"><div className="empty-icon"><KeyRound size={20}/></div><h3>Aucune clé API</h3><p>Les clés que vous créez pour cet espace apparaîtront ici.</p></div>}
    </section>
    <section className="api-key-docs"><b>Première requête</b><p>Utilisez le secret dans l’en-tête <code>Authorization: Bearer</code>. Ne l’intégrez jamais dans du code frontend public.</p><pre>{`curl -H "Authorization: Bearer VOTRE_CLE" "${window.location.origin}/api/v1/client/v1/datasets"`}</pre><span>La clé est en lecture seule. Le quota est de 120 requêtes par minute et par clé ; en cas de dépassement, attendez le délai indiqué par la réponse API. Les routes et paramètres sont documentés dans l’OpenAPI NOOMIN.</span></section>
  </>;
}
