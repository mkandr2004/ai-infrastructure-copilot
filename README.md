# AI Infrastructure Copilot

AI Infrastructure Copilot est un projet personnel orienté AI Engineering, MLOps et observabilité.

Son objectif est de surveiller une infrastructure Linux, de collecter ses métriques et ses logs, de conserver un historique dans PostgreSQL, puis d’utiliser un modèle d’intelligence artificielle pour produire des diagnostics prudents et structurés.

## État actuel

- **Phase 0 terminée** : diagnostic depuis le terminal avec `copilot_v0.py`.
- **Phase 1 terminée** : API FastAPI avec collecte système et diagnostic Gemini.
- **Phase 2 terminée** : stockage PostgreSQL, historique HTTP et surveillance périodique.
- **Tests automatiques** : 8 tests vérifient l’API, la surveillance et l’initialisation de la base sans appeler Gemini et sans modifier PostgreSQL.

L’application collecte l’utilisation du CPU, de la mémoire et du disque. Elle peut aussi récupérer les avertissements et erreurs de `journalctl`.

Les métriques peuvent être enregistrées périodiquement dans PostgreSQL puis consultées avec l’API. Les logs ne sont pas enregistrés dans PostgreSQL.

Le diagnostic par Gemini nécessite une confirmation explicite. L’envoi des logs à Gemini est désactivé par défaut.

## Architecture actuelle

    Machine Linux / WSL
            │
            ▼
    app/collectors/system.py
    collecte CPU, mémoire, disque et logs
            │
            ├──► copilot_v0.py
            │    diagnostic depuis le terminal
            │
            ├──► app/main.py
            │    API FastAPI
            │       │
            │       ├──► GET /health
            │       ├──► GET /metrics
            │       ├──► POST /diagnose ──► Gemini
            │       └──► GET /metrics/history
            │                         │
            │                         ▼
            │                  PostgreSQL
            │
            └──► app/monitoring.py
                 collecte périodique sans logs
                        │
                        ▼
                 app/services/metrics.py
                        │
                        ▼
                 SQLAlchemy + Psycopg
                        │
                        ▼
                 PostgreSQL

Le script terminal, l’API et la surveillance réutilisent le même collecteur.

La surveillance est exécutée séparément du serveur FastAPI afin d’éviter de lancer plusieurs boucles de collecte si l’API utilise plusieurs processus.

`app/services/metrics.py` centralise l’écriture et la lecture des instantanés. SQLAlchemy prépare les opérations de base de données, Psycopg communique avec PostgreSQL et Pydantic transforme les résultats en réponses JSON.

## Technologies utilisées

- Python
- psutil et journalctl
- FastAPI et Uvicorn
- Pydantic
- PostgreSQL
- SQLAlchemy et Psycopg
- Google Gen AI SDK
- pytest et TestClient
- Git

## Installation

### 1. Cloner le dépôt

    git clone URL_DU_DEPOT
    cd ai-infrastructure-copilot

### 2. Créer un environnement virtuel

    python3 -m venv .venv
    source .venv/bin/activate

### 3. Installer les dépendances

    python -m pip install --upgrade pip
    pip install -r requirements.txt

### 4. Installer et démarrer PostgreSQL

Sous Ubuntu ou WSL :

    sudo apt update
    sudo apt install postgresql postgresql-contrib
    sudo service postgresql start

Sur une nouvelle installation, ouvrir la console PostgreSQL :

    sudo -u postgres psql

Créer l’utilisateur et la base de l’application :

    CREATE USER ai_copilot_app
    WITH PASSWORD 'CHOISISSEZ_UN_MOT_DE_PASSE';

    CREATE DATABASE ai_infrastructure_copilot
    OWNER ai_copilot_app;

Quitter la console PostgreSQL :

    \q

Le mot de passe choisi ici devra être recopié dans `POSTGRES_PASSWORD` dans le fichier `.env`.

### 5. Configurer les variables d’environnement

Copier le modèle de configuration :

    cp .env.example .env
    chmod 600 .env

Compléter ensuite `.env` :

    # Gemini
    GEMINI_API_KEY=VOTRE_CLE
    GEMINI_MODEL=gemini-3.8-flash

    # PostgreSQL
    POSTGRES_HOST=localhost
    POSTGRES_PORT=5432
    POSTGRES_DB=ai_infrastructure_copilot
    POSTGRES_USER=ai_copilot_app
    POSTGRES_PASSWORD=LE_MOT_DE_PASSE_CHOISI

`GEMINI_API_KEY` est nécessaire uniquement pour demander un diagnostic. La configuration PostgreSQL est nécessaire pour charger l’API et utiliser la surveillance.

Le fichier `.env` contient des secrets et ne doit jamais être ajouté à Git.

### 6. Initialiser les tables

Créer les tables absentes :

    python -m app.db.init_db

Résultat attendu :

    Initialisation PostgreSQL terminée.
    Table disponible : metric_snapshots

Cette commande conserve les tables et les données déjà présentes. Elle crée uniquement les tables absentes.

## Utilisation

### Diagnostic depuis le terminal

    python copilot_v0.py

Le programme affiche les données préparées et demande une confirmation explicite avant l’appel à Gemini.

### Enregistrer une seule mesure

    python -m app.monitoring

Cette commande collecte CPU, mémoire et disque, puis ajoute un instantané dans PostgreSQL.

### Démarrer la surveillance périodique

Par exemple, pour enregistrer une mesure toutes les 60 secondes :

    python -m app.monitoring --interval 60

Arrêter proprement la surveillance avec `Ctrl+C`.

La surveillance n’enregistre pas les logs système. Si un cycle échoue, l’erreur est affichée et une nouvelle tentative est effectuée au cycle suivant.

## API FastAPI

Démarrer le serveur depuis la racine du projet :

    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

La documentation interactive est disponible sur <http://127.0.0.1:8000/docs>.

| Route | Rôle |
| --- | --- |
| `GET /health` | Vérifier que l’API répond. |
| `GET /metrics` | Consulter une mesure actuelle sans l’enregistrer. |
| `GET /metrics/history` | Lire les instantanés enregistrés dans PostgreSQL. |
| `POST /diagnose` | Demander un diagnostic à Gemini après confirmation. |

Consulter les dix mesures les plus récentes :

    curl "http://127.0.0.1:8000/metrics/history?limit=10"

La valeur de `limit` doit être comprise entre `1` et `1000`. Les résultats sont classés du plus récent au plus ancien.

Exemple de corps pour `POST /diagnose` :

    {
      "confirm_external_send": true,
      "include_logs": false
    }

`confirm_external_send` doit être `true` pour autoriser l’appel externe. Quand `include_logs` vaut `false`, les logs ne sont pas inclus dans le prompt envoyé à Gemini.

## Tests

Installer les dépendances de développement :

    python -m pip install -r requirements-dev.txt

Lancer les tests :

    python -m pytest -q

Les huit tests vérifient :

- la santé de l’API ;
- le refus d’un diagnostic sans confirmation ;
- l’exclusion des logs du diagnostic par défaut ;
- la réponse de `GET /metrics/history` ;
- la collecte et l’enregistrement sans logs ;
- le refus d’un intervalle invalide ;
- la nouvelle tentative après l’échec d’un cycle ;
- l’initialisation des tables SQLAlchemy.

Gemini, les attentes temporelles et les opérations PostgreSQL sont simulés pendant les tests. Aucun quota Gemini n’est consommé et aucune donnée de test n’est ajoutée à la vraie base.

## Sécurité

- les clés et mots de passe sont conservés dans `.env` ;
- `.env` est ignoré par Git ;
- `.env.example` contient uniquement des valeurs fictives ;
- l’utilisateur doit confirmer explicitement l’appel à Gemini ;
- les logs sont exclus du diagnostic par défaut ;
- les logs ne sont pas enregistrés par la surveillance PostgreSQL ;
- les erreurs affichent leur type sans révéler le mot de passe ou le contenu des données ;
- aucune action corrective n’est exécutée automatiquement.

## Roadmap

- Phase 0 terminée : script de diagnostic terminal
- Phase 1 terminée : API FastAPI
- Phase 2 terminée : surveillance continue et PostgreSQL
- Phase 3 prévue : RAG documentaire avec Qdrant
- Phase 4 prévue : mémoire des incidents avec Redis
- Phase 5 prévue : dashboard
- Phase 6 prévue : Docker et déploiement
- Phase 7 prévue : Prometheus et Grafana
- Phase 8 prévue : workflows et agents optionnels