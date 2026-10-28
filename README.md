# AI Infrastructure Copilot

AI Infrastructure Copilot est un projet personnel orienté AI Engineering, MLOps et observabilité.

Son objectif est de surveiller une infrastructure Linux, de collecter ses métriques et ses logs, de conserver un historique dans PostgreSQL, puis d’utiliser un modèle d’intelligence artificielle enrichi par une documentation technique locale pour produire des diagnostics prudents et structurés. Les incidents diagnostiqués peuvent être mémorisés temporairement dans Redis.

## État actuel

- **Phase 0 terminée** : diagnostic depuis le terminal avec `copilot_v0.py`.
- **Phase 1 terminée** : API FastAPI avec collecte système et diagnostic Gemini.
- **Phase 2 terminée** : stockage PostgreSQL, historique HTTP et surveillance périodique.
- **Phase 3 terminée** : RAG documentaire local avec embeddings Gemini et Qdrant.
- **Phase 4 terminée** : mémoire temporaire des incidents avec Redis et expiration automatique.
- **Tests automatiques** : 48 tests vérifient l’API, PostgreSQL, la surveillance, le pipeline RAG et la mémoire Redis sans consommer de quota Gemini.

L’application collecte l’utilisation du CPU, de la mémoire et du disque. Elle peut aussi récupérer les avertissements et erreurs de `journalctl`.

Les métriques peuvent être enregistrées périodiquement dans PostgreSQL puis consultées avec l’API. Les logs ne sont jamais enregistrés dans PostgreSQL.

Le diagnostic peut rechercher des passages pertinents dans une documentation locale consacrée au CPU, à la mémoire et au disque. Les passages retrouvés dans Qdrant sont ajoutés au prompt comme références techniques, sans être considérés comme des faits observés.

À la demande de l’utilisateur, le résultat d’un diagnostic peut être enregistré dans Redis avec un résumé des métriques et les sources documentaires utilisées. Les logs bruts ne sont jamais enregistrés dans l’incident.

Les appels à Gemini nécessitent toujours une confirmation explicite. L’envoi des logs est désactivé par défaut.

## Architecture actuelle

    Documents Markdown contrôlés
    knowledge/*.md
            │
            ▼
    app/rag/documents.py
    découpage en passages
            │
            ▼
    app/rag/embeddings.py ──────────────► Gemini Embeddings
            │
            ▼
    app/rag/indexer.py
            │
            ▼
    Qdrant local
    data/qdrant/
            │
            │ recherche sémantique
            ▼
    app/rag/retriever.py
            │
            ▼
    app/rag/context.py
    contexte documentaire sécurisé
            │
            └──────────────────────────────┐
                                           │
    Machine Linux / WSL                    │
            │                              │
            ▼                              │
    app/collectors/system.py               │
    CPU, mémoire, disque et logs           │
            │                              │
            ├──► copilot_v0.py             │
            │    diagnostic terminal       │
            │                              │
            ├──► app/main.py ◄─────────────┘
            │    API FastAPI
            │       │
            │       ├──► GET /health
            │       ├──► GET /metrics
            │       ├──► GET /metrics/history
            │       ├──► GET /incidents
            │       ├──► GET /incidents/{incident_id}
            │       └──► POST /diagnose
            │                    │
            │                    ▼
            │          métriques + problème signalé
            │          + contexte documentaire
            │                    │
            │                    ▼
            │             Gemini Diagnostic
            │                    │
            │                    │ enregistrement optionnel
            │                    ▼
            │          app/memory/incidents.py
            │                    │
            │                    ▼
            │                  Redis
            │          incidents temporaires + TTL
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

Le script terminal, l’API et la surveillance réutilisent le même collecteur système.

La surveillance est exécutée séparément du serveur FastAPI afin d’éviter de lancer plusieurs boucles de collecte si l’API utilise plusieurs processus.

PostgreSQL conserve l’historique des mesures numériques dans la table `metric_snapshots`. Qdrant conserve les vecteurs de la documentation technique. Redis conserve temporairement les incidents diagnostiqués. Chaque stockage a donc une responsabilité différente.

## Organisation du RAG

| Fichier | Rôle |
| --- | --- |
| `app/rag/documents.py` | Charge les fichiers Markdown et les découpe en passages. |
| `app/rag/embeddings.py` | Prépare les textes et demande leurs embeddings à Gemini. |
| `app/rag/vector_store.py` | Ouvre Qdrant et initialise la collection vectorielle. |
| `app/rag/indexer.py` | Transforme les passages en points Qdrant et synchronise l’index. |
| `app/rag/retriever.py` | Recherche les passages proches de la question. |
| `app/rag/context.py` | Formate les passages pour le prompt de diagnostic. |
| `app/rag/index_knowledge.py` | Fournit la commande d’indexation documentaire. |
| `app/rag/search_knowledge.py` | Fournit la commande de recherche documentaire. |
| `knowledge/` | Contient la documentation technique contrôlée. |
| `data/qdrant/` | Contient l’index local généré et ignoré par Git. |

Les identifiants des passages sont déterministes. Une nouvelle indexation remplace les passages existants portant le même identifiant et supprime les anciens points qui ne correspondent plus aux documents actuels.

## Mémoire des incidents

| Fichier | Rôle |
| --- | --- |
| `app/memory/redis_client.py` | Crée le client Redis et vérifie la connexion. |
| `app/memory/incidents.py` | Enregistre, lit et liste les incidents avec expiration automatique. |
| `app/schemas/incident.py` | Définit la structure validée d’un incident. |

Un incident contient notamment sa description, la date de collecte, un résumé CPU/mémoire/disque, le modèle utilisé, le diagnostic et les sources documentaires. Il ne contient pas les logs bruts.

L’enregistrement est optionnel et doit être demandé avec `save_incident: true`. Par défaut, un incident expire après 604 800 secondes, soit sept jours. Redis supprime alors automatiquement sa clé et l’application nettoie les références expirées de l’index lors des lectures suivantes.

Redis est une mémoire temporaire et non l’historique permanent des métriques. PostgreSQL reste responsable des mesures collectées dans le temps.

## Technologies utilisées

- Python
- psutil et journalctl
- FastAPI et Uvicorn
- Pydantic
- PostgreSQL
- SQLAlchemy et Psycopg
- Qdrant local
- Google Gen AI SDK
- Gemini Embeddings
- Redis
- redis-py
- pytest et TestClient
- Git

## Installation

### 1. Cloner le dépôt

    git clone https://github.com/mkandr2004/ai-infrastructure-copilot.git
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

Sur une nouvelle installation, ouvrir ensuite la console PostgreSQL :

    sudo -u postgres psql

Créer l’utilisateur et la base de l’application :

    CREATE USER ai_copilot_app
    WITH PASSWORD 'CHOISISSEZ_UN_MOT_DE_PASSE';

    CREATE DATABASE ai_infrastructure_copilot
    OWNER ai_copilot_app;

Quitter la console PostgreSQL :

    \q

Le mot de passe choisi ici devra être recopié dans `POSTGRES_PASSWORD` dans le fichier `.env`.

### 5. Installer et démarrer Redis

Sous Ubuntu ou WSL, installer Redis selon la documentation officielle, puis démarrer le service :

    sudo service redis-server start

Vérifier que le serveur répond :

    redis-cli ping

Résultat attendu :

    PONG

Redis est nécessaire uniquement pour enregistrer et consulter les incidents temporaires.

### 6. Configurer les variables d’environnement

Copier le modèle de configuration :

    cp .env.example .env
    chmod 600 .env

Compléter ensuite `.env` :

    # Gemini
    GEMINI_API_KEY=VOTRE_CLE
    GEMINI_MODEL=gemini-3.8-flash
    GEMINI_EMBEDDING_MODEL=gemini-embedding-2
    EMBEDDING_DIMENSIONS=768
    GEMINI_TIMEOUT_MS=30000
    GEMINI_RETRY_ATTEMPTS=1

    # PostgreSQL
    POSTGRES_HOST=localhost
    POSTGRES_PORT=5432
    POSTGRES_DB=ai_infrastructure_copilot
    POSTGRES_USER=ai_copilot_app
    POSTGRES_PASSWORD=LE_MOT_DE_PASSE_CHOISI

    # RAG et Qdrant
    QDRANT_PATH=data/qdrant
    QDRANT_COLLECTION=infrastructure_knowledge
    KNOWLEDGE_PATH=knowledge
    RAG_SCORE_THRESHOLD=0.72

    # Redis
    REDIS_HOST=localhost
    REDIS_PORT=6379
    REDIS_DB=0
    REDIS_PASSWORD=
    REDIS_KEY_PREFIX=ai_copilot
    INCIDENT_TTL_SECONDS=604800

`GEMINI_API_KEY` est nécessaire pour les diagnostics, l’indexation et les recherches documentaires.

`GEMINI_TIMEOUT_MS` limite la durée d’un appel Gemini et `GEMINI_RETRY_ATTEMPTS` limite les nouvelles tentatives automatiques du SDK.

La configuration PostgreSQL est nécessaire pour charger l’API et utiliser la surveillance.

La configuration Redis est nécessaire pour enregistrer ou consulter les incidents temporaires. Laisser `REDIS_PASSWORD` vide lorsque le serveur local n’exige pas d’authentification.

Le fichier `.env` contient des secrets et ne doit jamais être ajouté à Git.

### 7. Initialiser PostgreSQL

Créer les tables absentes :

    python -m app.db.init_db

Résultat attendu :

    Initialisation PostgreSQL terminée.
    Table disponible : metric_snapshots

Cette commande conserve les tables et les données existantes. Elle crée uniquement les tables absentes.

### 8. Préparer l’index documentaire

Afficher les passages qui seront traités sans effectuer d’appel externe :

    python -m app.rag.index_knowledge

Après vérification, autoriser la création des embeddings et l’indexation :

    python -m app.rag.index_knowledge \
      --confirm-external-send

La collection Qdrant est créée automatiquement si elle n’existe pas.

Une réindexation synchronise la collection avec les fichiers Markdown actuels. Les points correspondant à des passages supprimés sont également supprimés.

Une réindexation complète recalcule actuellement tous les embeddings et peut donc consommer du quota Gemini.

## Utilisation

### Diagnostic depuis le terminal

    python copilot_v0.py

Le programme affiche les données préparées et demande une confirmation explicite avant l’appel à Gemini.

### Enregistrer une seule mesure

    python -m app.monitoring

Cette commande collecte le CPU, la mémoire et le disque, puis ajoute un instantané dans PostgreSQL.

### Démarrer la surveillance périodique

Par exemple, pour enregistrer une mesure toutes les 60 secondes :

    python -m app.monitoring --interval 60

Arrêter proprement la surveillance avec `Ctrl+C`.

La surveillance n’enregistre pas les logs système. Si un cycle échoue, l’erreur est affichée et une nouvelle tentative est effectuée au cycle suivant.

### Rechercher dans la documentation

Une recherche nécessite la création externe d’un embedding.

    python -m app.rag.search_knowledge \
      "Le processeur reste à 95 %, comment identifier la cause ?" \
      --limit 3 \
      --confirm-external-send

Les passages dont le score est inférieur à `RAG_SCORE_THRESHOLD` sont ignorés. Qdrant peut ainsi retourner zéro résultat si la documentation n’est pas suffisamment pertinente.

## API FastAPI

Démarrer le serveur depuis la racine du projet :

    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

La documentation interactive est disponible sur <http://127.0.0.1:8000/docs>.

| Route | Rôle |
| --- | --- |
| `GET /health` | Vérifier que l’API répond. |
| `GET /metrics` | Consulter une mesure actuelle sans l’enregistrer. |
| `GET /metrics/history` | Lire les instantanés enregistrés dans PostgreSQL. |
| `POST /diagnose` | Demander un diagnostic Gemini, avec RAG optionnel. |
| `GET /incidents` | Lister les incidents temporaires du plus récent au plus ancien. |
| `GET /incidents/{incident_id}` | Lire un incident temporaire par son identifiant. |

Consulter les dix mesures les plus récentes :

    curl "http://127.0.0.1:8000/metrics/history?limit=10"

La valeur de `limit` doit être comprise entre `1` et `1000`. Les résultats sont classés du plus récent au plus ancien.

### Diagnostic sans recherche documentaire

    {
      "confirm_external_send": true,
      "include_logs": false,
      "use_knowledge": false,
      "problem_description": "Le serveur semble lent.",
      "save_incident": false
    }

### Diagnostic enrichi par le RAG

    {
      "confirm_external_send": true,
      "include_logs": false,
      "use_knowledge": true,
      "problem_description": "Le processeur reste à 95 %, comment identifier la cause ?",
      "save_incident": true
    }

`confirm_external_send` doit être `true` pour autoriser les appels externes.

`save_incident` vaut `false` par défaut. Quand il vaut `true`, `problem_description` est obligatoire et le diagnostic réussi est enregistré dans Redis.

La réponse contient alors :

- `incident_saved`, qui indique si l’enregistrement Redis a réussi ;
- `incident_id`, qui contient l’identifiant de l’incident enregistré ou `null`.

Une indisponibilité de Redis n’annule pas un diagnostic Gemini déjà obtenu : la réponse conserve le diagnostic avec `incident_saved: false`.

Consulter les incidents enregistrés :

    curl "http://127.0.0.1:8000/incidents?limit=20"
    curl "http://127.0.0.1:8000/incidents/IDENTIFIANT_INCIDENT"

Quand `include_logs` vaut `false`, les logs ne sont pas inclus dans le prompt envoyé à Gemini.

Quand `use_knowledge` vaut `true`, `problem_description` est obligatoire. L’application crée d’abord un embedding de cette description, recherche les passages pertinents dans Qdrant, puis envoie le contexte retenu avec les métriques à Gemini.

Une requête RAG utilise donc normalement deux appels externes :

1. un appel pour l’embedding de la recherche ;
2. un appel pour le diagnostic final.

La réponse contient également :

- `knowledge_used`, qui indique si un contexte documentaire a été ajouté ;
- `knowledge_sources`, qui liste les fichiers sources des passages retrouvés.

Si aucun passage ne dépasse le seuil de pertinence, le diagnostic continue sans contexte documentaire.

## Tests

Installer les dépendances de développement :

    python -m pip install -r requirements-dev.txt

Lancer les tests :

    python -m pytest -q

Les 48 tests couvrent notamment :

- les routes principales de l’API ;
- la confirmation obligatoire avant un appel externe ;
- l’exclusion des logs par défaut ;
- l’historique PostgreSQL ;
- la collecte périodique et ses erreurs ;
- l’initialisation des tables ;
- le découpage des documents Markdown ;
- la préparation et la validation des embeddings ;
- l’initialisation de Qdrant ;
- l’indexation et la synchronisation des points ;
- la recherche sémantique et son seuil ;
- la construction sécurisée du contexte documentaire ;
- le diagnostic avec ou sans passage pertinent ;
- le traitement des erreurs de recherche documentaire ;
- la configuration des délais Gemini et le traitement explicite du quota `429` ;
- la connexion Redis simulée ;
- l’enregistrement, l’expiration, la lecture et la liste des incidents ;
- le comportement de l’API lorsque Redis est indisponible.

Gemini et Redis sont simulés pendant les tests de l’API. Qdrant utilise une base en mémoire et les opérations PostgreSQL sont isolées ou simulées.

Les tests ne consomment aucun quota Gemini et n’ajoutent aucune donnée dans la vraie base PostgreSQL, l’index Qdrant persistant ou le serveur Redis réel.

## Sécurité

- les clés et mots de passe sont conservés dans `.env` ;
- `.env` est ignoré par Git ;
- `.env.example` contient uniquement des valeurs fictives ;
- l’utilisateur doit confirmer explicitement chaque opération nécessitant Gemini ;
- les documents sont affichés avant leur indexation externe ;
- les logs sont exclus du diagnostic par défaut ;
- les logs ne sont pas enregistrés dans PostgreSQL ;
- les passages documentaires sont traités comme des données non fiables ;
- les instructions éventuellement présentes dans les logs ou les documents doivent être ignorées ;
- les erreurs n’affichent ni les secrets ni le contenu complet des prompts ;
- l’enregistrement d’un incident est désactivé par défaut ;
- les incidents enregistrés ne contiennent pas les logs bruts ;
- chaque incident possède une durée de conservation limitée ;
- une erreur de quota Gemini reçoit une réponse HTTP `429` explicite ;
- aucune action corrective n’est exécutée automatiquement.

## Limites actuelles

- Qdrant fonctionne en mode local persistant, adapté au développement et à une utilisation mono-processus.
- Les documents pris en charge sont actuellement des fichiers Markdown.
- Une réindexation recalcule tous les embeddings, même si certains passages n’ont pas changé.
- Le seuil de pertinence `0.72` est empirique et devra être réévalué lorsque le corpus documentaire grandira.
- Le corpus actuel couvre principalement les incidents CPU, mémoire et disque.
- Les diagnostics reposent sur des mesures ponctuelles sauf si l’historique est consulté séparément.
- L’application propose des vérifications, mais n’exécute aucune correction automatique.
- Redis est utilisé comme mémoire temporaire locale et non comme stockage d’archive permanent.
- Les routes d’incidents ne possèdent pas encore d’authentification et sont destinées à un environnement local de développement.
- Les quotas et limites de débit Gemini dépendent du projet Google AI utilisé et peuvent bloquer temporairement les appels externes.

## Roadmap

- Phase 0 terminée : script de diagnostic terminal
- Phase 1 terminée : API FastAPI
- Phase 2 terminée : surveillance continue et PostgreSQL
- Phase 3 terminée : RAG documentaire avec Qdrant
- Phase 4 terminée : mémoire temporaire des incidents avec Redis
- Phase 5 prévue : dashboard
- Phase 6 prévue : Docker et déploiement
- Phase 7 prévue : Prometheus et Grafana
- Phase 8 prévue : workflows et agents optionnels