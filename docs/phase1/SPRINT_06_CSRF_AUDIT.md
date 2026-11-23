# NOOMIN — Phase 1, Sprint 06 : CSRF et journal d’audit

**Objectif :** protéger les mutations par cookie et tracer les actions importantes par organisation.  
**État :** implémenté et vérifié.

## Protection CSRF

- Chaque session reçoit un cookie de session HTTP-only et un cookie CSRF lisible côté interface.
- Le jeton CSRF est une HMAC liée au jeton de session ; l’interface le transmet en `X-CSRF-Token` pour les mutations.
- L’API valide les origines déclarées, bloque les requêtes `Sec-Fetch-Site: cross-site` et vérifie le cookie/header CSRF lié à la session.
- Les réponses de connexion, inscription, session et invitation maintiennent le cookie CSRF ; la déconnexion le supprime.
- Les cookies préexistants sans jeton CSRF restent protégés par la validation stricte de l’origine et le contrôle `Sec-Fetch-Site` pendant la transition.

## Journal d’audit

- Migration Alembic `0008_audit_logs`, modèle et route paginée `GET /api/v1/audit`.
- Consultation réservée aux propriétaires et administrateurs et limitée côté requête à l’organisation active.
- Événements suivis : création d’organisation, import/suppression CSV, analyses sauvegardées, création/lancement pipeline, rôle membre modifié, membre retiré, invitation créée/révoquée/acceptée.
- Les métadonnées sont construites depuis une liste de champs sûrs ; aucune valeur de ligne CSV, aucun mot de passe et aucun token d’invitation ne sont journalisés.
- Interface « Journal d’audit » avec pagination et détails des événements.
- En mode aperçu SQLite, les tables d’audit, d’invitation et de limiteur sont créées de façon additive ; le jeton CSRF est stateless et n’ajoute aucune table.

## Limites

- Pas encore de politique de rétention, d’export, ni de signature cryptographique des lignes du journal.
- Le contrôle d’origine dépend de `CORS_ORIGINS` ; le déploiement doit déclarer les domaines exacts.
- Le flux accepte les clients sans en-tête `Origin` pour permettre les clients non navigateur ; les navigateurs doivent envoyer l’origine et le jeton CSRF.
- La migration PostgreSQL est vérifiée par génération SQL, mais pas appliquée à un serveur PostgreSQL réel.

## Vérification

- Tests API : **23 réussis** sous Python 3.12.14.
- Build frontend, lint, `git diff --check` et génération SQL Alembic réussis.
- Un avertissement connu concerne la dépréciation de `Starlette TestClient` avec `httpx`.
