# NOOMIN — Phase 1, Sprint 05 : limitation des connexions

**Objectif :** ralentir les attaques par essais répétés de mots de passe avec un état partagé par les processus API.  
**État :** implémenté et vérifié.

## Livré

- Table `auth_login_throttles` et migration Alembic `0007_auth_login_throttle`.
- 10 échecs par combinaison compte/adresse IP et 60 échecs par adresse IP sur une fenêtre de 15 minutes ; les tentatives bloquées reçoivent HTTP 429 et `Retry-After`.
- État stocké en base avec upsert atomique PostgreSQL/SQLite ; il ne repose pas sur la mémoire d’un seul serveur.
- Les clés sont des HMAC du compte et/ou de l’adresse IP ; aucune adresse IP ni e-mail de limitation n’est stocké dans cette table.
- Compteurs supprimés après expiration ; un succès réinitialise le compteur propre au compte.
- Mode aperçu SQLite : création additive de la nouvelle table au démarrage.
- Test vérifiant le blocage, le délai et le retour à la connexion après expiration.

## Limites

- Le contrôle protège la route de connexion ; il ne constitue pas un limiteur global de toutes les routes publiques.
- L’adresse distante dépend du proxy ; le déploiement devra configurer correctement les en-têtes et hôtes proxy de confiance.
- La migration est générée en SQL PostgreSQL, mais n’a pas été appliquée sur un serveur PostgreSQL réel pendant cette validation.

## Vérification

- Tests API : **21 réussis** sous Python 3.12.14.
- Build frontend, lint, `git diff --check` et génération SQL Alembic réussis.
- Un avertissement connu concerne la dépréciation de `Starlette TestClient` avec `httpx`.
