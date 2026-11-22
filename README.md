# NOOMIN — MVP Business Intelligence

NOOMIN est le nom de travail du produit. La disponibilité de la marque et du domaine reste à vérifier.

## Ce qui fonctionne

- Création de compte avec une organisation et un rôle propriétaire ; connexion et déconnexion par cookie de session HTTP-only.
- Accès aux données limité aux organisations auxquelles le compte appartient. Le rôle `viewer` peut consulter sans importer.
- Import d’un CSV UTF-8 (10 Mo maximum, 20 000 lignes et 200 colonnes maximum), stockage des valeurs dans PostgreSQL et aperçu paginé des 100 premières lignes.
- Profil descriptif calculé sur les valeurs importées : type de colonne, valeurs présentes/distinctes et distribution des colonnes numériques.
- Interface React/TypeScript responsive, Vite, Tailwind et composants selon les conventions shadcn/ui.

Pipelines planifiés, connecteurs externes, graphiques enregistrés, invitations, IA, facturation et vérification d’e-mail ne sont pas encore implémentés. L’interface les identifie comme indisponibles. Aucun service de données ou modèle IA externe n’est présenté comme connecté.

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

Les mots de passe sont hachés avec Argon2id et le cookie est HTTP-only, `SameSite=Lax`, avec l’attribut `Secure` hors développement. Remplacez tous les identifiants de développement et utilisez une clé JWT aléatoire avant tout déploiement.

Ce MVP n’inclut pas encore la vérification d’adresse e-mail, la limitation de tentatives de connexion, l’invalidation serveur de sessions déjà émises, la gestion des invitations, les sauvegardes, les journaux d’audit ni une revue de sécurité de production. Le health check est un contrôle de disponibilité applicative ; il ne valide pas PostgreSQL ou Redis.

### Aperçu local sans Docker

Pour essayer l’interface et le parcours CSV sans installer PostgreSQL, un aperçu local peut utiliser SQLite. Ce mode est réservé au développement et n’applique pas les migrations PostgreSQL :

```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
export DATABASE_URL=sqlite:///../../work/noomin-preview.sqlite
export JWT_SECRET_KEY=local-noomin-preview-secret-key-32-chars
python -c 'from noomin_api.db.session import engine; from noomin_api.db.base import Base; import noomin_api.models; Base.metadata.create_all(engine)'
uvicorn noomin_api.main:app --reload
```

Dans un second terminal, à la racine du dépôt : `npm install && npm run dev`. Les inscriptions et imports de ce mode sont conservés dans `work/noomin-preview.sqlite` sur cette machine.
