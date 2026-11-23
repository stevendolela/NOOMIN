# NOOMIN — Phase 1, Sprint 01 : fondations des permissions

**Objectif :** rendre les rôles explicitement différents côté API et empêcher les paramètres de développement les plus risqués en environnement production.  
**État :** implémentation faite ; QA acceptée ; revue Sécurité sans bloqueur.  
**Périmètre :** ce sprint ne livre pas encore invitations, administration des membres, déploiement production ni audit de sécurité.

## Travail livré

- Ajout d’une matrice centrale dans `apps/api/noomin_api/api/permissions.py`.
- Permissions définies : lecture, édition des données, gestion des membres et gestion du workspace.
- Rôles actuels :
  - `owner` : toutes les permissions.
  - `admin` : lecture, édition et gestion des membres.
  - `member` : lecture et édition des données ; affiché comme **Analyste** dans l’interface pour rester compatible avec les adhésions déjà enregistrées.
  - `viewer` : lecture seulement.
- Import, suppression d’import, sauvegarde d’analyse et mutations de pipeline utilisent maintenant le contrôle commun d’édition.
- Tous les environnements hors `development`, `dev`, `local` et `test` refusent certains marqueurs JWT de développement et les origines CORS wildcard `*`.
- Le README décrit les permissions centralisées et le rôle Analyste côté interface.

## Fichiers concernés

- Créé : `apps/api/noomin_api/api/permissions.py`, `apps/api/tests/test_settings.py`.
- Modifiés : `apps/api/noomin_api/api/datasets.py`, `apps/api/noomin_api/api/analyses.py`, `apps/api/noomin_api/api/pipelines.py`, `apps/api/noomin_api/core/config.py`, `apps/api/tests/test_auth_and_datasets.py`, `apps/web/src/App.tsx`, `README.md`.

## Validation

- Tests API : **16 réussis** sous Python 3.12.14, avec un avertissement de dépréciation `Starlette TestClient` / `httpx`.
- Frontend : `npm run build` réussi ; `npm run lint` réussi.
- Contrôle du diff : `git diff --check` réussi.

## Décisions

1. Garder `member` comme valeur persistée plutôt que migrer tous les tenants ; le produit l’appelle Analyste.
2. Préparer les permissions de gestion des membres et du workspace, mais ne pas les exposer avant la création des routes/API correspondantes.
3. Le garde-fou production vérifie seulement les valeurs de configuration de l’API ; il ne rend pas le Compose actuel prêt pour la production.

## Limites et suites

- Aucun endpoint de gestion des membres/invitations n’existe encore ; `MANAGE_MEMBERS` n’est donc pas encore consommée par une route.
- La protection CSRF explicite, la limitation des tentatives de connexion et la vérification d’adresse restent à faire.
- Les identifiants et ports de développement dans Compose, Redis sans authentification et le démarrage Uvicorn avec rechargement restent à traiter avant toute exposition partagée.
- Les changements n’ont pas été validés avec Docker, PostgreSQL ou Redis réels.
- Prochain lot recommandé : historique complet des exécutions et contrat de statut des jobs, puis sélection d’organisation et invitations avec tests cross-tenant.

## Revue

- QA : acceptée ; les tests d’intégration confirment qu’un viewer ne peut importer, sauvegarder une analyse ou lancer un pipeline.
- Security : aucun bloqueur dans la matrice et le garde-fou de configuration ; restent les secrets de base de données/Redis, la robustesse du secret choisi, CSRF et le rate limiting.
