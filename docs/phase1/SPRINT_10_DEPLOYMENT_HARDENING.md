# Sprint 10 — Durcissement du déploiement

## Objectif

Réduire les risques de configuration avant d’ajouter des intégrations métier, sans présenter une configuration locale comme un déploiement de production validé.

## Réalisé

- Toute requête de mutation portant une session doit fournir le cookie CSRF et l’en-tête `X-CSRF-Token`. Les deux valeurs doivent correspondre au jeton signé lié à la session, même si l’en-tête `Origin` est absent.
- PostgreSQL et Redis ne publient plus de ports hôte dans la configuration Compose de base. Redis exige un mot de passe et son healthcheck s’authentifie.
- Les paramètres sensibles requis (mots de passe, URL de connexion, clé JWT, environnement et origines CORS) ne retombent plus sur des valeurs de développement dans la configuration Compose de base.
- Les ports locaux, le montage du code source, le rechargement automatique et les migrations au démarrage sont isolés dans `docker-compose.dev.yml`.
- Un service de maintenance dédié applique les migrations Alembic. L’image API s’exécute sous un utilisateur non-root.
- Ajout d’un healthcheck pour l’interface Nginx et mise à jour des instructions d’installation et de déploiement.
- Les URL PostgreSQL standard de Supabase (`postgresql://` et `postgres://`) sont converties automatiquement vers le pilote psycopg 3, pour l’API comme pour Alembic.

## Vérifications effectuées

- `pytest` sur la suite API : **31 tests réussis**.
- Vérification syntaxique des deux fichiers Compose en YAML : réussie.
- `git diff --check` : aucune erreur d’espacement.

## Limites et suite recommandée

Docker n’est pas installé dans l’environnement de travail. La résolution effective de `docker compose config`, la construction des images et un démarrage avec PostgreSQL/Redis réels n’ont donc pas pu être vérifiés. Les tests API s’appuient sur leur configuration de test et ne remplacent pas cette validation d’intégration.

Avant un déploiement partagé, il reste à tester le profil de maintenance et le démarrage complet sur un hôte Docker, installer un ingress HTTPS, confirmer les sauvegardes/restaurations PostgreSQL et définir la rétention des journaux d’audit. Les paramètres du fichier `.env` doivent être remplacés par des secrets propres à chaque environnement.
