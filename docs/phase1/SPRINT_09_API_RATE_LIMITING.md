# NOOMIN — Phase 1, Sprint 09 : limitation de débit API

**Objectif :** limiter l’impact d’un usage excessif ou d’une fuite de clé API.
**État :** implémenté et vérifié en tests ; intégration à un Redis de déploiement réel à valider avec Compose.

## Changements

- Quota fixe de **120 appels par minute et par clé API**, toutes les routes client v1 confondues.
- Compteur Redis atomique via Lua, partagé entre workers API ; expiration automatique du compteur à la fin de la fenêtre.
- Réponses avec `X-RateLimit-Limit`, `X-RateLimit-Remaining` et `X-RateLimit-Reset` ; dépassement renvoyé en `429` avec `Retry-After`.
- En environnement de production, une panne Redis fait échouer la requête en `503` plutôt que de désactiver silencieusement la protection.
- En SQLite aperçu/test, compteur local au processus pour fonctionner sans Redis. Il ne convient pas au multi-worker et ne s’applique qu’au développement.
- Documentation utilisateur mise à jour dans README et dans l’écran Accès API.

## Vérification

- Tests API : **28 réussis**, dont l’épuisement du quota et le mode fermé en cas de panne Redis en production.
- Build et lint frontend réussis.
- La génération SQL Alembic reste en `0009_api_keys` ; ce sprint n’ajoute pas de migration.

## Limite

Docker/Redis n’étant pas disponibles dans l’environnement courant, le script Lua n’a pas été exécuté contre un serveur Redis réel. Le test emploie un faux Redis et confirme les comportements de quota et d’erreur ; le partage entre plusieurs workers reste à valider au démarrage réel Compose.
