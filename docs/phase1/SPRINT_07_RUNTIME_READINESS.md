# NOOMIN — Phase 1, Sprint 07 : disponibilité des services

**Objectif :** rendre le démarrage Compose observable et expliciter les dépendances nécessaires à un pilote.
**État :** contrôles applicatifs implémentés et vérifiés localement ; validation Docker/PostgreSQL réelle à exécuter sur une machine équipée de Docker.

## Changements

- Ajout de `GET /api/v1/ready`, qui renvoie `200` seulement si PostgreSQL et Redis répondent, sinon `503`.
- Conservation de `GET /api/v1/health` comme contrôle existant de l’API et de PostgreSQL.
- Healthcheck Compose de l’API sur sa route readiness et du worker par ping Celery.
- L’interface attend maintenant que l’API soit saine avant son démarrage.
- README complété avec la procédure de vérification Compose et la lecture de la révision Alembic courante.

## Vérification

- Tests API : **24 réussis**.
- Build et lint frontend réussis.
- Génération complète du SQL Alembic PostgreSQL jusqu’à `0008_audit_logs` réussie.
- Syntaxe YAML de `docker-compose.yml` et `git diff --check` vérifiés.

## À vérifier avec Docker

Docker/Compose n’est pas installé dans l’environnement de développement utilisé pour ce sprint. Il reste donc à lancer `docker compose up --build`, vérifier l’état `healthy` des cinq services, confirmer la révision de migration dans PostgreSQL et effectuer le parcours manuel d’inscription, import CSV, analyse et pipeline avec le worker réel. La génération SQL ne prouve pas qu’une migration a été appliquée à PostgreSQL.

Les scénarios de sauvegarde/restauration, de panne/reprise Redis et de reprise après erreur d’un job Celery restent aussi nécessaires avant un pilote privé.
