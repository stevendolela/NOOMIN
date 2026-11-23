# NOOMIN — Phase 1, Sprint 08 : accès client par API

**Objectif :** permettre aux clients d’accéder à leurs données NOOMIN par API, sans exposition directe de PostgreSQL.
**État :** implémenté et vérifié localement ; migration PostgreSQL à appliquer lors d’un démarrage Docker réel.

## Clés d’organisation

- Migration `0009_api_keys` et modèle `OrganizationAPIKey` avec organisation, créateur, nom, scopes, dates d’expiration/usage/révocation, préfixe visible et hash du secret.
- Création et révocation depuis **Accès API**, réservé au propriétaire de l’organisation ; 20 clés actives maximum par organisation.
- Secret aléatoire présenté une seule fois ; seul son SHA-256 est enregistré. Expiration par défaut : 90 jours, réglable jusqu’à 365 jours.
- Scopes initiaux en lecture seule : `datasets:read` et `profiles:read`.
- Audit de la création et de la révocation ; mise à jour du dernier usage.
- Réponses externes marquées `Cache-Control: no-store`.

## API client v1

- `GET /api/v1/client/v1/datasets`
- `GET /api/v1/client/v1/datasets/{dataset_id}`
- `GET /api/v1/client/v1/datasets/{dataset_id}/rows?limit=100&offset=0` (maximum 1 000 lignes par page)
- `GET /api/v1/client/v1/datasets/{dataset_id}/profile` (scope `profiles:read`)

La clé détermine l’organisation ; aucune organisation choisie par l’appelant n’est acceptée pour ces routes. Les datasets et lignes sont toujours filtrés par ce tenant. Toute opération de modification via l’API client est exclue de cette première version.

## Vérification

- Tests API : **26 réussis**, dont création, secret non récupérable, scopes, révocation, refus d’accès hors tenant et contrôle propriétaire.
- Build et lint frontend réussis.
- Génération SQL PostgreSQL de la migration jusqu’à `0009_api_keys` réussie.
- `git diff --check` réussi.

## Limites avant exposition de production

- Docker/PostgreSQL n’étant pas disponibles dans cet environnement, la migration n’a pas été appliquée à une vraie base et Compose n’a pas été lancé.
- Ajouter une limitation de débit dédiée aux clés API et des alertes d’usage anormal avant une exposition publique.
- L’API v1 ne gère que les jeux CSV NOOMIN ; elle ne connecte pas encore les bases privées du client, et ne fournit pas de fonctions d’écriture.
