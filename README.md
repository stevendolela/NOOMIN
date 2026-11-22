# NOOMIN — socle SaaS

NOOMIN est le nom de travail du produit. La vérification de disponibilité de marque et de domaine reste à faire.

Ce dépôt contient un socle exécutable pour un SaaS B2B de Business Intelligence, Data Engineering et IA :

- `apps/web` : React + TypeScript + Vite, Tailwind CSS et interface responsive en français. Les composants suivent les conventions visuelles shadcn/ui et sont prêts à être extraits en composants réutilisables.
- `apps/api` : Python 3.12, FastAPI, SQLAlchemy 2, Pydantic Settings et Alembic.
- PostgreSQL 16 pour le stockage, Redis 7 comme broker/backend Celery, un worker Celery et Docker Compose.
- Modèle initial : organisations, utilisateurs et memberships avec rôles `owner`, `admin`, `member`, `viewer`.

L’interface n’invente pas de données métier : elle présente des états vides jusqu’à la connexion réelle de sources. Aucun fournisseur de données, service IA, authentification ou système de facturation n’est configuré.

## Prérequis

- Docker Engine et Docker Compose v2
- Node.js 22+ et npm 10+ pour le développement frontend local
- Python 3.12 pour le développement API local

## Démarrage complet avec Docker

```bash
cp .env.example .env
# Modifiez au minimum POSTGRES_PASSWORD avant un environnement partagé.
docker compose up --build
```

L’interface sera disponible sur <http://localhost:5173>, l’API sur <http://localhost:8000>, la documentation OpenAPI sur <http://localhost:8000/docs>, et le contrôle de santé sur <http://localhost:8000/api/v1/health>. Au démarrage de l’API, Compose applique la migration initiale. PostgreSQL et Redis ont des healthchecks ; API et worker attendent leur disponibilité.

## Développement local

Frontend :

```bash
npm install
npm run dev
```

API (depuis `apps/api`) :

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp ../../.env.example ../../.env
# Chargez les variables puis utilisez l'adresse hôte de PostgreSQL.
set -a && source ../../.env && set +a
export DATABASE_URL=postgresql+psycopg://noomin:noomin_dev_only@localhost:5432/noomin
alembic upgrade head
uvicorn noomin_api.main:app --reload
```

L’API locale nécessite PostgreSQL et Redis accessibles, ou les services `db` et `redis` lancés avec Compose. Les URLs d’environnement par défaut dans `.env.example` sont prévues pour les conteneurs Compose.

## Tests et build

```bash
cd apps/api && pytest
cd ../.. && npm run build
```

## Structure

```text
apps/
  api/
    alembic/                 Migrations versionnées
    noomin_api/
      api/                   Routes HTTP
      core/                  Configuration
      db/                    Base et sessions SQLAlchemy
      models/                Modèles de persistance
      schemas/               Contrats Pydantic
      tasks.py               Point d’extension des tâches
      worker.py              Configuration Celery
    tests/
  web/
    src/                     Interface React et styles
Dockerfile.api
Dockerfile.web
docker-compose.yml
```

## Points de sécurité avant déploiement

Le contrôle `/api/v1/health` est un contrôle de disponibilité de l’application (liveness) et ne prétend pas valider les connexions PostgreSQL ou Redis.

Le fichier `.env.example` utilise des identifiants réservés au développement. Remplacez-les avant tout déploiement partagé. Le socle n’implémente pas encore l’authentification, l’autorisation par tenant dans les requêtes, le chiffrement/gestion des secrets, la journalisation d’audit, la sauvegarde, ni des contrôles de production. Le modèle définit les appartenances, mais les routes métier et l’isolation runtime restent à construire.
