# NOOMIN — MVP Business Intelligence

NOOMIN est le nom de travail du produit. La disponibilité de la marque et du domaine reste à vérifier.

## Ce qui fonctionne

- Création de compte avec une organisation et un rôle propriétaire ; connexion et déconnexion par cookie de session HTTP-only.
- Accès aux données limité aux organisations auxquelles le compte appartient. Les rôles `owner`, `admin`, `member` (Analyste dans l’interface) et `viewer` disposent de permissions distinctes centralisées.
- Sélecteur d’organisation pour les comptes multi-organisation ; propriétaires et administrateurs peuvent lister les membres, modifier les rôles autorisés et retirer les adhésions. L’organisation conserve toujours au moins un propriétaire.
- Invitations par lien secret à usage unique, valables 7 jours, avec acceptation et création du compte invité ; le lien doit être partagé manuellement, aucun e-mail n’est envoyé.
- Connexions protégées par une limite persistée : 10 échecs par compte/adresse IP ou 60 échecs par adresse IP sur 15 minutes ; les identifiants de limitation sont stockés sous forme HMAC.
- Mutations navigateur protégées par validation de l’origine et jeton CSRF signé lié à la session ; journal d’audit tenant-scoped des imports/suppressions, analyses, pipelines, membres et invitations, consultable par propriétaire/administrateur.
- API client en lecture seule via des clés API rattachées à une organisation, avec scopes, expiration, révocation, journal des créations/révocations et accès paginé aux lignes CSV. La clé complète n’est affichée qu’une fois lors de sa création ; seul son hash est conservé.
- Import d’un CSV UTF-8 (10 Mo maximum, 20 000 lignes et 200 colonnes maximum), stockage des valeurs dans PostgreSQL et aperçu paginé des 100 premières lignes.
- Suppression d’un jeu de données depuis la liste, réservée aux rôles pouvant modifier ; les analyses et pipelines qui dépendent de la source sont également supprimés après confirmation.
- Profil descriptif calculé sur les valeurs importées : type de colonne, valeurs présentes/distinctes et distribution des colonnes numériques ; les distributions peuvent être enregistrées comme analyses dans l’organisation.
- Pipelines réels de sélection/renommage de colonnes et filtrage, exécutés en arrière-plan par Celery ; leurs résultats sont enregistrés comme nouveaux jeux de données.
- Interface React/TypeScript responsive, Vite, Tailwind et composants selon les conventions shadcn/ui.

Planification récurrente, connecteurs externes, tableaux de bord composables, envoi d’invitations par e-mail, IA, facturation et vérification d’e-mail ne sont pas encore implémentés. Aucun service de données ou modèle IA externe n’est présenté comme connecté.

Le MFA, le SSO client (Microsoft Entra ID / Active Directory fédéré) et le provisioning d’annuaire sont également à venir ; le périmètre prévu est suivi dans [la feuille de route identité](docs/phase1/IDENTITY_ROADMAP.md).

### API client

Un propriétaire crée une clé dans **Accès API**. Elle donne uniquement les droits de lecture choisis et est liée à l’organisation active lors de sa création. L’API ne prend pas d’identifiant d’organisation fourni par le client : elle déduit le tenant de la clé.

- `GET /api/v1/client/v1/datasets`
- `GET /api/v1/client/v1/datasets/{dataset_id}`
- `GET /api/v1/client/v1/datasets/{dataset_id}/rows?limit=100&offset=0`
- `GET /api/v1/client/v1/datasets/{dataset_id}/profile` (scope `profiles:read`)

Présentez le secret comme `Authorization: Bearer <clé>`. Les clés expirent par défaut après 90 jours (réglable entre 1 et 365 jours) et un propriétaire peut les révoquer dans l’interface. La première version est en lecture seule et plafonne une page à 1 000 lignes. Le quota est de 120 requêtes par minute et par clé, partagé par Redis en environnement avec PostgreSQL ; l’aperçu SQLite utilise un compteur local au processus. Ne mettez jamais une clé dans le code frontend livré au navigateur. Avant une exposition de production, appliquer et vérifier la migration PostgreSQL sur l’environnement déployé.

## Démarrage complet

Prérequis : Docker Engine avec Docker Compose v2.

```bash
cp .env.example .env
# Remplacez les mots de passe PostgreSQL/Redis (mot de passe Redis URL-safe) et JWT_SECRET_KEY.
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

- Interface : <http://localhost:5173>
- API : <http://localhost:8000>
- Documentation OpenAPI : <http://localhost:8000/docs>
- Liveness API : <http://localhost:8000/api/v1/health>
- Readiness (PostgreSQL + Redis) : <http://localhost:8000/api/v1/ready>

Compose attend que PostgreSQL et Redis soient prêts. La surcharge de développement applique les migrations Alembic au démarrage de l’API. Nginx sert l’interface et relaie `/api/` vers FastAPI. Redis exige un mot de passe ; les ports hôte et les volumes de code source n’existent que dans la surcharge de développement et sont liés à `127.0.0.1`.
La configuration de base ne publie aucun port hôte, ne monte pas le code source et ne lance pas Uvicorn en mode rechargement automatique. La surcharge `docker-compose.dev.yml` ajoute ces commodités pour le développement local. Pour un environnement partagé, configurez `ENVIRONMENT=production`, des secrets propres à l’environnement et `CORS_ORIGINS` avec le domaine exact, puis appliquez les migrations explicitement :

```bash
docker compose --profile maintenance run --rm migrate
docker compose up -d --build
```

La configuration ne fournit pas de reverse proxy TLS public : l’ingress de déploiement doit router vers le service `web` et terminer TLS. Gardez PostgreSQL et Redis sur le réseau interne Compose.
Compose expose l’état des services : l’API n’est prête qu’après connexion à PostgreSQL et Redis, le worker est vérifié par un ping Celery, et Nginx répond à son healthcheck.

Après le démarrage, vérifiez les services et la révision de base :

```bash
docker compose ps
docker compose exec api alembic -c alembic.ini current
```

Les services `db`, `redis`, `api`, `worker` et `web` doivent être `healthy`. L’interface de contrôle comprend ensuite l’inscription, l’import d’un CSV, le profil de données et la création puis l’exécution d’un pipeline. Cette vérification manuelle avec des conteneurs réels reste nécessaire sur une machine avec Docker ; elle n’est pas exécutée par les tests locaux.

## Développement local

L’API attend PostgreSQL et Redis accessibles. Démarrer les services de données avec `docker compose -f docker-compose.yml -f docker-compose.dev.yml up db redis`, puis dans un autre terminal :

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
set -a && source ../../.env && set +a
export DATABASE_URL=postgresql+psycopg://noomin:VOTRE_MOT_DE_PASSE_POSTGRES@localhost:5432/noomin
export REDIS_URL=redis://:VOTRE_MOT_DE_PASSE_REDIS@localhost:6379/0
alembic upgrade head
uvicorn noomin_api.main:app --reload
```

Dans un autre terminal, à la racine du dépôt :

```bash
npm install
npm run dev
```

Vite relaie les appels `/api/` vers l’API sur `localhost:8000`.

## Tests et build

```bash
cd apps/api && pytest
cd ../.. && npm run build && npm run lint
```

## Sécurité et limites de déploiement

Les mots de passe sont hachés avec Argon2id. Le cookie de session est HTTP-only et `SameSite=Lax`; toute mutation authentifiée par cookie exige un cookie et un en-tête CSRF signés liés à la session. Les cookies portent l’attribut `Secure` hors développement. La déconnexion révoque côté serveur les jetons de session de l’utilisateur. Les permissions sont contrôlées côté API selon le rôle. Hors environnements locaux/de test, l’API refuse certains secrets JWT de développement connus et les origines CORS wildcard (`*`). Ce contrôle ne remplace pas la génération et la gestion d’un secret robuste. Le health check vérifie PostgreSQL et répond `503` si la base est indisponible. Remplacez tous les identifiants de développement avant tout déploiement.

Ce MVP n’inclut pas encore la vérification d’adresse e-mail, des sauvegardes ni une revue de sécurité de production. Les journaux d’audit n’ont pas encore de politique de rétention. La limitation actuelle concerne les connexions et ne remplace pas une protection globale contre les abus. Le health check ne vérifie pas Redis ni le worker Celery.

### Aperçu local sans Docker

Pour essayer l’interface et le parcours CSV sans installer PostgreSQL, un aperçu local peut utiliser SQLite. Ce mode est réservé au développement et n’applique pas les migrations PostgreSQL :

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
export DATABASE_URL=sqlite:///../../work/noomin-preview.sqlite
export JWT_SECRET_KEY=local-noomin-preview-secret-key-32-chars
export CELERY_TASK_ALWAYS_EAGER=true
alembic upgrade head
uvicorn noomin_api.main:app --reload
```

Dans un second terminal, à la racine du dépôt : `npm install && npm run dev`. Les inscriptions, imports et résultats de pipeline de ce mode sont conservés dans `work/noomin-preview.sqlite` sur cette machine. Les tâches Celery s’exécutent localement en mode eager, sans Redis ; Compose utilise Redis et le worker pour les traitements asynchrones. Le mode SQLite crée automatiquement les tables additives des invitations, limiteurs de connexion, journaux d’audit et clés API si elles manquent, sans modifier les tables ni données existantes.
