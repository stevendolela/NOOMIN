# NOOMIN — Phase 1, Sprint 02 : historique des pipelines

**Objectif :** rendre consultables les exécutions persistées des pipelines, avec un statut explicite et une isolation par organisation.  
**État :** implémenté et vérifié.

## Livré

- Route `GET /api/v1/pipelines/{pipeline_id}/runs` avec pagination `limit` (1–100) et `offset`.
- Réponse incluant la liste des exécutions et le total, triées de la plus récente à la plus ancienne.
- Accès limité aux pipelines de l’organisation active ; un pipeline d’un autre tenant est masqué par une réponse 404.
- Historique repliable dans les cartes de pipelines : statut, date et heure, durée des exécutions terminées et message d’erreur si présent.
- Chargement à la demande et conservation de la limite de 20 derniers runs dans l’interface.
- Test API vérifiant le contenu de l’historique et l’isolation inter-organisation.

## Fichiers concernés

- Modifiés : `apps/api/noomin_api/api/pipelines.py`, `apps/api/noomin_api/schemas/pipeline.py`, `apps/api/tests/test_auth_and_datasets.py`, `apps/web/src/components/PipelineManager.tsx`, `apps/web/src/lib/types.ts`, `apps/web/src/styles.css`.

## Vérification

- Tests API : **16 réussis** sous Python 3.12.14.
- Frontend : build et lint réussis.
- `git diff --check` réussi.
- Un avertissement de dépréciation connu concerne `Starlette TestClient` avec `httpx`.

## Limites

- L’interface charge les 20 dernières exécutions ; l’API accepte la pagination, mais les contrôles de page suivants ne sont pas encore exposés dans l’interface.
- Pas de relance depuis l’historique, d’export ni de journal détaillé des étapes.
- Le déploiement PostgreSQL/Redis réel et les tests Docker restent à faire.
