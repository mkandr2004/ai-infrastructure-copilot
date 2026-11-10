# AI Infrastructure Copilot

AI Infrastructure Copilot est un projet personnel orienté AI Engineering, MLOps et observabilité.

Son objectif est de surveiller une infrastructure Linux, de collecter ses métriques et ses logs, de conserver un historique dans PostgreSQL, puis d’utiliser un modèle d’intelligence artificielle enrichi par une documentation technique locale pour produire des diagnostics prudents et structurés. Les incidents et les workflows d’investigation peuvent être mémorisés temporairement dans Redis. Prometheus collecte les métriques opérationnelles de l’API et Grafana les présente dans un dashboard dédié.

## État actuel

- **Phase 0 terminée** : diagnostic depuis le terminal avec `copilot_v0.py`.
- **Phase 1 terminée** : API FastAPI avec collecte système et diagnostic Gemini.
- **Phase 2 terminée** : stockage PostgreSQL, historique HTTP et surveillance périodique.
- **Phase 3 terminée** : RAG documentaire local avec embeddings Gemini et Qdrant.
- **Phase 4 terminée** : mémoire temporaire des incidents avec Redis et expiration automatique.
- **Phase 5 terminée** : dashboard web pour les métriques, l’historique, les incidents et les diagnostics.
- **Phase 6 terminée** : conteneurisation Docker et orchestration locale avec Docker Compose.
- **Phase 7 terminée** : exposition de métriques Prometheus et visualisation avec un dashboard Grafana provisionné automatiquement.
- **Phase 8 terminée** : workflows d’investigation contrôlés avec étapes traçables, analyse déterministe et diagnostic Gemini.
- **Phase 9 terminée** : exécution asynchrone des workflows, règles Prometheus, Alertmanager, mémoire Redis des alertes et notifications webhook optionnelles.
- **Tests automatiques** : 129 tests vérifient l’API, les stockages, le RAG, les dashboards, l’observabilité, les workflows, l’alerting et le déploiement sans consommer de quota Gemini.

L’application collecte l’utilisation du CPU, de la mémoire et du disque. Elle peut aussi récupérer les avertissements et erreurs de `journalctl`.

Les métriques peuvent être enregistrées périodiquement dans PostgreSQL puis consultées avec l’API. Les logs ne sont jamais enregistrés dans PostgreSQL.

Le diagnostic peut rechercher des passages pertinents dans une documentation locale consacrée au CPU, à la mémoire et au disque. Les passages retrouvés dans Qdrant sont ajoutés au prompt comme références techniques, sans être considérés comme des faits observés.

À la demande de l’utilisateur, le résultat d’un diagnostic peut être enregistré dans Redis avec un résumé des métriques et les sources documentaires utilisées. Les logs bruts ne sont jamais enregistrés dans l’incident.

Les appels à Gemini nécessitent toujours une confirmation explicite. L’envoi des logs est désactivé par défaut.

Le dashboard web rassemble les métriques actuelles, l’historique PostgreSQL, les incidents Redis et le formulaire de diagnostic Gemini dans une interface responsive servie directement par FastAPI.

Un workflow d’investigation est placé dans une file Redis puis traité par un worker séparé. Il enchaîne de manière contrôlée la collecte actuelle, l’historique PostgreSQL, les incidents Redis similaires, la documentation Qdrant, des constats CPU/mémoire/disque déterministes et un diagnostic final Gemini. Chaque étape est enregistrée dans Redis et aucune correction n’est exécutée automatiquement.

L’API expose également des métriques au format Prometheus. Prometheus les collecte toutes les 15 secondes et Grafana fournit une vue opérationnelle sur la disponibilité, le trafic HTTP, les latences et l’utilisation des ressources.

Prometheus évalue cinq règles d’alerte pour la disponibilité, le CPU, la mémoire, le disque et les erreurs HTTP 5xx. Alertmanager groupe les alertes, les transmet à un webhook FastAPI authentifié, puis l’application les conserve temporairement dans Redis et peut envoyer un résumé vers un webhook externe optionnel.

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
            │       ├──► GET /dashboard
            │       ├──► GET /metrics
            │       ├──► GET /metrics/prometheus ──► Prometheus ──► Grafana
            │       ├──► GET /metrics/history
            │       ├──► GET /incidents
            │       ├──► GET /incidents/{incident_id}
            │       ├──► POST /diagnose
            │       ├──► POST /workflows
            │       ├──► GET /workflows
            │       ├──► GET /workflows/{workflow_id}
            │       ├──► POST /alerts/webhook ◄── Alertmanager ◄── Prometheus
            │       └──► GET /alerts
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

## Workflows d’investigation

| Fichier | Rôle |
| --- | --- |
| `app/schemas/workflow.py` | Définit les états, étapes, constats et réponses d’un workflow. |
| `app/workflows/storage.py` | Crée, met à jour, lit et liste les workflows dans Redis. |
| `app/workflows/lifecycle.py` | Contrôle les transitions d’état du workflow et de ses étapes. |
| `app/workflows/analyzers.py` | Produit des constats CPU, mémoire et disque selon des seuils explicites. |
| `app/workflows/similarity.py` | Recherche des incidents similaires par comparaison textuelle déterministe. |
| `app/workflows/context.py` | Formate les constats et incidents historiques sans recopier leurs anciens diagnostics. |
| `app/workflows/runner.py` | Orchestre les six étapes et persiste chaque transition. |
| `app/workflows/queue.py` | Place et retire les identifiants de workflows dans une file Redis. |
| `app/workflows/worker.py` | Consomme la file séparément de l’API et exécute les investigations. |
| `app/workflows/router.py` | Expose la mise en file, la liste et la lecture des workflows. |

Les six étapes sont :

1. collecte des métriques actuelles ;
2. analyse des cent dernières mesures PostgreSQL ;
3. recherche d’incidents Redis similaires ;
4. recherche documentaire Qdrant optionnelle ;
5. production de constats déterministes CPU, mémoire et disque ;
6. génération du diagnostic final avec Gemini.

Les étapes possèdent les états `pending`, `running`, `completed`, `skipped` ou `failed`. Le workflow possède les états `pending`, `queued`, `running`, `completed` ou `failed`. Un échec est conservé dans Redis afin de rendre visible l’étape qui a échoué. Par défaut, un workflow expire après 86 400 secondes, soit 24 heures.

`POST /workflows` répond immédiatement avec le statut HTTP `202` et un workflow `queued`. Le service `workflow-worker` le traite en arrière-plan, tandis que le dashboard interroge périodiquement `GET /workflows/{id}` jusqu’à l’état final. Les constats reposent sur des seuils transparents de 80 % pour un avertissement et 90 % pour un niveau critique.

## Dashboard web

| Fichier | Rôle |
| --- | --- |
| `app/dashboard/router.py` | Sert la page HTML sur `GET /dashboard`. |
| `app/dashboard/templates/dashboard.html` | Structure accessible de l’interface. |
| `app/dashboard/static/dashboard.css` | Mise en page sombre et responsive. |
| `app/dashboard/static/dashboard.js` | Charge les métriques actuelles et l’historique. |
| `app/dashboard/static/dashboard-chart.js` | Dessine les tendances avec un SVG natif. |
| `app/dashboard/static/dashboard-operations.js` | Gère Redis et le formulaire de diagnostic. |
| `app/dashboard/static/dashboard-workflows.js` | Lance, liste et affiche les workflows d’investigation. |
| `app/dashboard/static/dashboard-alerts.js` | Charge et affiche les alertes récentes conservées dans Redis. |

Le dashboard n’ajoute aucun framework frontend ni CDN. Il utilise Jinja2, CSS, JavaScript et SVG natifs. Les contenus provenant des incidents, des workflows et des diagnostics sont insérés avec `textContent` afin de ne pas interpréter leur contenu comme du HTML.

## Observabilité Prometheus et Grafana

| Fichier | Rôle |
| --- | --- |
| `app/observability/metrics.py` | Définit les compteurs, histogrammes et jauges Prometheus. |
| `app/observability/middleware.py` | Mesure le nombre, le statut et la durée des requêtes HTTP. |
| `app/observability/router.py` | Expose les métriques sur `GET /metrics/prometheus`. |
| `deploy/prometheus/prometheus.yml` | Configure la collecte de l’API toutes les 15 secondes. |
| `deploy/grafana/provisioning/` | Configure automatiquement la source Prometheus et le fournisseur de dashboards. |
| `deploy/grafana/dashboards/infrastructure-overview.json` | Définit le dashboard opérationnel et ses sept panneaux. |

Les métriques personnalisées utilisent le préfixe `ai_copilot_`. Elles couvrent le nombre de requêtes HTTP, leur durée, l’utilisation du CPU, l’utilisation et la mémoire disponible, ainsi que l’utilisation et l’espace disponible sur le disque.

Prometheus conserve quinze jours de séries temporelles dans un volume Docker persistant. Grafana utilise Prometheus comme source par défaut et charge automatiquement le dashboard **AI Infrastructure Copilot** au démarrage.

Le dashboard FastAPI et le dashboard Grafana sont complémentaires : le premier sert à utiliser l’application et à demander des diagnostics, tandis que le second sert à observer son fonctionnement dans le temps.

## Alertes Prometheus et Alertmanager

| Fichier | Rôle |
| --- | --- |
| `deploy/prometheus/rules/alerts.yml` | Définit les cinq règles d’alerte et leur durée minimale. |
| `deploy/alertmanager/alertmanager.yml.template` | Groupe les alertes et configure le webhook applicatif authentifié. |
| `docker/render-alertmanager-config.sh` | Injecte le secret au démarrage sans le versionner dans Git. |
| `app/alerts/router.py` | Authentifie le webhook et expose `GET /alerts`. |
| `app/alerts/storage.py` | Normalise et conserve temporairement les alertes dans Redis. |
| `app/alerts/notifications.py` | Envoie facultativement un résumé vers un webhook externe. |
| `app/schemas/alert.py` | Valide les messages Alertmanager et les réponses de l’API. |

Une alerte n’est pas déclenchée par une pointe unique : chaque règle possède une durée `for`. Alertmanager envoie également les résolutions. Le secret `ALERT_WEBHOOK_TOKEN` doit être long et aléatoire ; il est comparé de manière sûre par l’API. Une panne du webhook de notification externe n’empêche pas la conservation de l’alerte dans Redis.

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
- Jinja2
- HTML, CSS et JavaScript
- Docker
- Docker Compose
- Prometheus
- prometheus-client
- Grafana
- Alertmanager
- SVG natif
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
    GEMINI_MODEL=gemini-3.5-flash-lite
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
    WORKFLOW_TTL_SECONDS=86400
    WORKFLOW_QUEUE_NAME=investigation-workflows
    WORKFLOW_WORKER_POLL_SECONDS=2
    ALERT_TTL_SECONDS=604800
    ALERT_WEBHOOK_TOKEN=UN_SECRET_LONG_ET_ALEATOIRE
    NOTIFICATION_WEBHOOK_URL=
    NOTIFICATION_TIMEOUT_SECONDS=5

`GEMINI_API_KEY` est nécessaire pour les diagnostics, l’indexation et les recherches documentaires.

`GEMINI_TIMEOUT_MS` limite la durée d’un appel Gemini et `GEMINI_RETRY_ATTEMPTS` limite les nouvelles tentatives automatiques du SDK.

La configuration PostgreSQL est nécessaire pour charger l’API et utiliser la surveillance.

La configuration Redis est nécessaire pour enregistrer ou consulter les incidents et workflows temporaires. Laisser `REDIS_PASSWORD` vide lorsque le serveur local n’exige pas d’authentification.

`INCIDENT_TTL_SECONDS`, `WORKFLOW_TTL_SECONDS` et `ALERT_TTL_SECONDS` contrôlent les durées de conservation. `NOTIFICATION_WEBHOOK_URL` est facultative. Générer par exemple le secret Alertmanager avec `openssl rand -hex 32`.

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

## Déploiement avec Docker Compose

Docker Compose lance huit services isolés :

| Service | Rôle |
| --- | --- |
| `app` | Sert FastAPI, le dashboard et l’API sur le port local configuré. |
| `monitoring` | Collecte périodiquement les métriques et les écrit dans PostgreSQL. |
| `workflow-worker` | Consomme la file Redis et exécute les investigations en arrière-plan. |
| `postgres` | Conserve l’historique permanent des métriques. |
| `redis` | Conserve temporairement les incidents diagnostiqués. |
| `prometheus` | Collecte et conserve les métriques opérationnelles de l’API. |
| `alertmanager` | Groupe les alertes et les transmet au webhook authentifié de l’API. |
| `grafana` | Visualise les séries Prometheus dans un dashboard provisionné. |

Qdrant reste embarqué dans le conteneur applicatif et écrit son index dans un volume Docker persistant.

### Prérequis Docker

Installer Docker Engine avec le plugin Docker Compose, ou Docker Desktop avec l’intégration WSL activée.

Vérifier ensuite les commandes :

    docker --version
    docker compose version

### Configuration Docker

Créer la configuration locale si elle n’existe pas encore :

    cp .env.example .env
    chmod 600 .env

`POSTGRES_PASSWORD` doit obligatoirement contenir un vrai mot de passe. `GEMINI_API_KEY` reste optionnelle tant qu’aucun diagnostic ou embedding externe n’est demandé.

`ALERT_WEBHOOK_TOKEN` et `GRAFANA_ADMIN_PASSWORD` sont également obligatoires avec Compose. Ils doivent contenir des secrets distincts et non versionnés.

Les variables `POSTGRES_HOST` et `REDIS_HOST` peuvent rester à `localhost` pour l’exécution native. Compose les remplace automatiquement par les noms internes `postgres` et `redis` dans les conteneurs.

Les paramètres spécifiques au déploiement sont :

| Variable | Valeur par défaut | Rôle |
| --- | --- | --- |
| `APP_PORT` | `8000` | Port local du dashboard et de l’API. |
| `MONITORING_INTERVAL_SECONDS` | `60` | Intervalle entre deux mesures enregistrées. |
| `PROMETHEUS_PORT` | `9090` | Port local de l’interface Prometheus. |
| `ALERTMANAGER_PORT` | `9093` | Port local de l’interface Alertmanager. |
| `GRAFANA_PORT` | `3000` | Port local de l’interface Grafana. |
| `GRAFANA_ADMIN_USER` | `admin` | Identifiant administrateur initial de Grafana. |
| `GRAFANA_ADMIN_PASSWORD` | aucune | Mot de passe administrateur Grafana obligatoire dans `.env`. |

### Démarrage

Construire l’image et démarrer les huit services :

    docker compose up --build --detach

Vérifier leur état et la santé de l’API :

    docker compose ps
    curl http://127.0.0.1:8000/health

Les interfaces locales sont disponibles aux adresses suivantes :

- dashboard applicatif : <http://127.0.0.1:8000/dashboard> ;
- Prometheus : <http://127.0.0.1:9090> ;
- Alertmanager : <http://127.0.0.1:9093> ;
- Grafana : <http://127.0.0.1:3000>.

Au premier démarrage, l’entrypoint attend PostgreSQL puis crée les tables absentes. Les conteneurs applicatifs sont exécutés avec un utilisateur non privilégié. PostgreSQL, Redis, Qdrant, Prometheus et Grafana utilisent des volumes nommés persistants.

Grafana demande l’identifiant et le mot de passe configurés dans `.env`. La source Prometheus et le dashboard sont déjà provisionnés : aucune configuration manuelle n’est nécessaire après la connexion.

### Indexation RAG dans Docker

Après le démarrage, indexer la documentation avec une commande ponctuelle :

    docker compose run --rm app \
      python -m app.rag.index_knowledge \
      --confirm-external-send

Cette opération utilise la clé Gemini configurée et peut consommer du quota d’embeddings.

### Exploitation et arrêt

Suivre les journaux applicatifs :

    docker compose logs --follow app monitoring workflow-worker alertmanager

Arrêter les conteneurs sans supprimer les données :

    docker compose down

Les volumes PostgreSQL, Redis et Qdrant sont conservés. La commande suivante les supprime définitivement et ne doit être utilisée que pour une remise à zéro volontaire :

    docker compose down --volumes

Le port applicatif est lié à `127.0.0.1` uniquement. Le déploiement n’est donc pas exposé directement sur le réseau. Un déploiement distant nécessitera un reverse proxy HTTPS, une authentification et une politique de sauvegarde.

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
| `GET /dashboard` | Ouvrir le tableau de bord web. |
| `GET /metrics` | Consulter une mesure actuelle sans l’enregistrer. |
| `GET /metrics/prometheus` | Exposer les métriques au format Prometheus. |
| `GET /metrics/history` | Lire les instantanés enregistrés dans PostgreSQL. |
| `POST /diagnose` | Demander un diagnostic Gemini, avec RAG optionnel. |
| `GET /incidents` | Lister les incidents temporaires du plus récent au plus ancien. |
| `GET /incidents/{incident_id}` | Lire un incident temporaire par son identifiant. |
| `POST /workflows` | Créer et mettre en file un workflow d’investigation. |
| `GET /workflows` | Lister les workflows temporaires du plus récent au plus ancien. |
| `GET /workflows/{workflow_id}` | Lire un workflow et le résultat de chaque étape. |
| `POST /alerts/webhook` | Recevoir un lot Alertmanager avec authentification Bearer. |
| `GET /alerts` | Lister les alertes temporaires, avec filtre de statut optionnel. |

Consulter les dix mesures les plus récentes :

    curl "http://127.0.0.1:8000/metrics/history?limit=10"

La valeur de `limit` doit être comprise entre `1` et `1000`. Les résultats sont classés du plus récent au plus ancien.

### Dashboard

Après le démarrage d’Uvicorn, ouvrir :

    http://127.0.0.1:8000/dashboard

Le dashboard permet de consulter les métriques actuelles, visualiser l’historique PostgreSQL, lire les incidents Redis, lancer des workflows d’investigation et demander un diagnostic Gemini. L’envoi des logs et les appels externes restent des choix explicites.

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

### Workflow d’investigation

Lancer une investigation complète sans envoyer les logs :

    curl -X POST "http://127.0.0.1:8000/workflows" \
      -H "Content-Type: application/json" \
      -d '{
        "problem_description": "Le CPU reste régulièrement à 95 %.",
        "confirm_external_send": true,
        "include_logs": false,
        "use_knowledge": true
      }'

Consulter ensuite les workflows temporaires :

    curl "http://127.0.0.1:8000/workflows?limit=20"
    curl "http://127.0.0.1:8000/workflows/IDENTIFIANT_WORKFLOW"

La confirmation externe est obligatoire, car le diagnostic final utilise Gemini et la recherche documentaire peut créer un embedding externe. Lorsque `use_knowledge` vaut `false`, l’étape documentaire est enregistrée avec l’état `skipped`.

Les descriptions des incidents historiques sont traitées comme des données non fiables. Leurs anciens diagnostics ne sont pas injectés dans le nouveau prompt. Les métriques actuelles restent prioritaires.

La création retourne immédiatement un statut `queued`. Le worker réalise ensuite l’investigation. Le client doit relire le workflow jusqu’à `completed` ou `failed` ; le dashboard effectue ce suivi automatiquement.

### Alertes récentes

Consulter toutes les alertes ou uniquement celles encore actives :

    curl "http://127.0.0.1:8000/alerts?limit=20"
    curl "http://127.0.0.1:8000/alerts?limit=20&status=firing"

La route d’écriture est réservée à Alertmanager et exige `Authorization: Bearer ...`. Elle ne doit pas être appelée par le dashboard.

## Tests

Installer les dépendances de développement :

    python -m pip install -r requirements-dev.txt

Lancer les tests :

    python -m pytest -q

Les 129 tests couvrent notamment :

- les routes principales de l’API ;
- la structure, la sécurité et les dépendances du déploiement Docker Compose ;
- le rendu du dashboard et la disponibilité de ses ressources statiques ;
- l’exposition des métriques système et HTTP au format Prometheus ;
- l’instrumentation des requêtes et la normalisation des labels de routes ;
- la configuration de collecte Prometheus et le provisioning Grafana ;
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
- la validation des schémas de workflow ;
- le stockage, l’index et l’expiration Redis des workflows ;
- les transitions contrôlées des étapes ;
- les seuils des analyseurs CPU, mémoire et disque ;
- la recherche déterministe d’incidents similaires ;
- la séparation du contexte d’investigation dans le prompt ;
- l’orchestration complète, les erreurs et les routes des workflows.
- la file Redis, le worker asynchrone et le suivi du statut `queued` ;
- les règles Prometheus et la configuration Alertmanager ;
- l’authentification du webhook, le stockage Redis et la notification optionnelle ;
- l’affichage des alertes dans le dashboard.

Gemini et Redis sont simulés pendant les tests de l’API. Qdrant utilise une base en mémoire et les opérations PostgreSQL sont isolées ou simulées.

Les tests ne consomment aucun quota Gemini et n’ajoutent aucune donnée dans la vraie base PostgreSQL, l’index Qdrant persistant ou le serveur Redis réel.

Le rendu HTML et la disponibilité des fichiers CSS et JavaScript du dashboard sont également couverts par les tests.

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
- chaque workflow possède une durée de conservation limitée ;
- chaque alerte possède une durée de conservation limitée ;
- le webhook Alertmanager exige un secret Bearer partagé qui n’est pas versionné ;
- une panne de notification externe ne supprime pas l’alerte locale ;
- les anciens diagnostics ne sont pas réinjectés dans un nouveau workflow ;
- chaque étape du workflow est limitée à des lectures et des analyses ;
- une erreur de quota Gemini reçoit une réponse HTTP `429` explicite ;
- aucune action corrective n’est exécutée automatiquement ;
- le dashboard exige une confirmation explicite avant l’appel à Gemini ;
- l’image Docker exclut `.env`, `.git`, les données locales et l’environnement virtuel ;
- les conteneurs applicatifs utilisent un utilisateur non privilégié et un système de fichiers racine en lecture seule ;
- PostgreSQL et Redis ne publient aucun port sur la machine hôte ;
- l’API, Prometheus et Grafana sont liés uniquement à l’interface locale `127.0.0.1` ;
- l’inscription anonyme et la création libre de comptes Grafana sont désactivées ;
- les contenus externes sont affichés comme du texte et non interprétés comme du HTML.

## Limites actuelles

- Qdrant fonctionne en mode local persistant, adapté au développement et à une utilisation mono-processus.
- Les documents pris en charge sont actuellement des fichiers Markdown.
- Une réindexation recalcule tous les embeddings, même si certains passages n’ont pas changé.
- Le seuil de pertinence `0.72` est empirique et devra être réévalué lorsque le corpus documentaire grandira.
- Le corpus actuel couvre principalement les incidents CPU, mémoire et disque.
- Le diagnostic rapide repose sur une mesure ponctuelle ; le workflow analyse jusqu’aux cent dernières mesures PostgreSQL.
- L’application propose des vérifications, mais n’exécute aucune correction automatique.
- Redis est utilisé comme mémoire temporaire locale et non comme stockage d’archive permanent.
- Les routes d’incidents ne possèdent pas encore d’authentification et sont destinées à un environnement local de développement.
- Les quotas et limites de débit Gemini dépendent du projet Google AI utilisé et peuvent bloquer temporairement les appels externes.
- Le dashboard ne possède pas encore d’authentification et doit rester accessible uniquement depuis l’hôte local.
- Les graphiques SVG n’offrent pas encore de zoom ou d’infobulles interactives.
- Dans Docker, les métriques décrivent le conteneur applicatif et non l’ensemble de la machine hôte.
- Prometheus conserve actuellement quinze jours de métriques ; les seuils d’alerte sont génériques et doivent être adaptés à chaque environnement.
- Le dashboard Grafana est provisionné en lecture seule depuis les fichiers versionnés du dépôt.
- La file Redis locale convient à un worker unique ; une production distribuée nécessiterait des mécanismes supplémentaires de réservation, nouvelle tentative et file d’échec.
- La similarité des incidents repose actuellement sur les mots partagés, sans embedding supplémentaire.
- Les seuils de 80 % et 90 % sont génériques et devront être adaptés à chaque infrastructure.
- `journalctl` n’est généralement pas disponible dans le conteneur applicatif.

## Roadmap

- Phase 0 terminée : script de diagnostic terminal
- Phase 1 terminée : API FastAPI
- Phase 2 terminée : surveillance continue et PostgreSQL
- Phase 3 terminée : RAG documentaire avec Qdrant
- Phase 4 terminée : mémoire temporaire des incidents avec Redis
- Phase 5 terminée : dashboard web opérationnel
- Phase 6 terminée : Docker et déploiement local avec Compose
- Phase 7 terminée : métriques Prometheus et dashboard Grafana
- Phase 8 terminée : workflows d’investigation contrôlés et analyseurs spécialisés
- Phase 9 terminée : alertes Prometheus, Alertmanager, notifications et exécution asynchrone
