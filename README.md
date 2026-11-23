# NOOMIN — MVP Business Intelligence

NOOMIN est le nom de travail du produit. La disponibilité de la marque et du domaine reste à vérifier.

## Ce qui fonctionne

- Création de compte avec une organisation et un rôle propriétaire ; connexion et déconnexion par cookie de session HTTP-only.
- Accès aux données limité aux organisations auxquelles le compte appartient. Les rôles `owner`, `admin`, `member` (Analyste dans l’interface) et `viewer` disposent de permissions distinctes centralisées.
- Sélecteur d’organisation pour les comptes multi-organisation ; propriétaires et administrateurs peuvent lister les membres, modifier les rôles autorisés et retirer les adhésions. L’organisation conserve toujours au moins un propriétaire.
- Invitations par lien secret à usage unique, valables 7 jours, avec acceptation et création du compte invité ; le lien doit être partagé manuellement, aucun e-mail n’est envoyé.
- Connexions protégées par une limite persistée : 10 échecs par compte/adresse IP ou 60 échecs par adresse IP sur 15 minutes ; les identifiants de limitation sont stockés sous forme HMAC.
- Import d’un CSV UTF-8 (10 Mo maximum, 20 000 lignes et 200 colonnes maximum), stockage des valeurs dans PostgreSQL et aperçu paginé des 100 premières lignes.
- Suppression d’un jeu de données depuis la liste, réservée aux rôles pouvant modifier ; les analyses et pipelines qui dépendent de la source sont également supprimés après confirmation.
- Profil descriptif calculé sur les valeurs importées : type de colonne, valeurs présentes/distinctes et distribution des colonnes numériques ; les distributions peuvent être enregistrées comme analyses dans l’organisation.
- Pipelines réels de sélection/renommage de colonnes et filtrage, exécutés en arrière-plan par Celery ; leurs résultats sont enregistrés comme nouveaux jeux de données.
- Interface React/TypeScript responsive, Vite, Tailwind et composants selon les conventions shadcn/ui.

Planification récurrente, connecteurs externes, tableaux de bord composables, envoi d’invitations par e-mail, IA, facturation et vérification d’e-mail ne sont pas encore implémentés. Aucun service de données ou modèle IA externe n’est présenté comme connecté.

## Démarrage complet

Prérequis : Docker Engine avec Docker Compose v2.

```bash
cp .env.example .env
# Définissez un JWT_SECRET_KEY aléatoire d'au moins 32 caractères et changez POSTGRES_PASSWORD.
docker compose up --build
```

- Interface : <http://localhost:5173>
- API : <http://localhost:8000>
- Documentation OpenAPI : <http://localhost:8000/docs>
- Liveness : <http://localhost:8000/api/v1/health>

Compose attend que PostgreSQL et Redis soient prêts. L’API applique les migrations Alembic avant de démarrer. Nginx sert l’interface et relaie `/api/` vers FastAPI.

## Développement local

L’API attend PostgreSQL et Redis accessibles. Démarrer les services de données avec `docker compose up db redis`, puis dans un autre terminal :

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
set -a && source ../../.env && set +a
export DATABASE_URL=postgresql+psycopg://noomin:noomin_dev_only@localhost:5432/noomin
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

Les mots de passe sont hachés avec Argon2id et le cookie est HTTP-only, `SameSite=Lax`, avec l’attribut `Secure` hors développement. La déconnexion révoque côté serveur les jetons de session de l’utilisateur. Les permissions sont contrôlées côté API selon le rôle. Hors environnements locaux/de test, l’API refuse certains secrets JWT de développement connus et les origines CORS wildcard (`*`). Ce contrôle ne remplace pas la génération et la gestion d’un secret robuste. Le health check vérifie PostgreSQL et répond `503` si la base est indisponible. Remplacez tous les identifiants de développement avant tout déploiement.

Ce MVP n’inclut pas encore la vérification d’adresse e-mail, des sauvegardes, des journaux d’audit ni une revue de sécurité de production. La limitation actuelle concerne les connexions et ne remplace pas une protection globale contre les abus. Le health check ne vérifie pas Redis ni le worker Celery.

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

Dans un second terminal, à la racine du dépôt : `npm install && npm run dev`. Les inscriptions, imports et résultats de pipeline de ce mode sont conservés dans `work/noomin-preview.sqlite` sur cette machine. Les tâches Celery s’exécutent localement en mode eager, sans Redis ; Compose utilise Redis et le worker pour les traitements asynchrones. Le mode SQLite crée automatiquement la table additive des invitations si elle manque, sans modifier les tables ni données existantes.
