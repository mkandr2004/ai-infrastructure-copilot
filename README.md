# AI Infrastructure Copilot

AI Infrastructure Copilot est un projet personnel orienté AI Engineering, MLOps et observabilité.

Son objectif est de surveiller une infrastructure Linux, de collecter ses métriques et ses logs, puis d’utiliser un modèle d’intelligence artificielle pour générer des diagnostics prudents et structurés.

## État actuel

- **Phase 0 terminée** : diagnostic depuis le terminal avec `copilot_v0.py`.
- **Phase 1 terminée** : API FastAPI avec collecte des données système et diagnostic Gemini.
- **Tests automatiques** : 3 tests réussis pour vérifier l’API sans appeler Gemini.

L’application collecte un instantané de l’utilisation du CPU, de la mémoire et du disque. Elle peut aussi récupérer des logs système. Le diagnostic par Gemini nécessite une confirmation explicite ; l’envoi des logs est désactivé par défaut.

## Architecture actuelle

```text
Machine Linux / WSL
        │
        ▼
app/collectors/system.py ── collecte des métriques et des logs
        │
        ├──► copilot_v0.py ── utilisation dans le terminal
        │
        └──► app/main.py ── API FastAPI
                  │
                  ├── app/core/config.py ── configuration et clé API
                  └── app/services/diagnosis.py ── prompt et appel Gemini

tests/test_api.py ── tests automatiques de l’API
```

Le script terminal et l’API réutilisent le même collecteur : on évite de maintenir deux versions différentes de la collecte.

## Technologies utilisées

- Python
- psutil
- journalctl
- Google Gen AI SDK
- python-dotenv
- Git

## Installation

### 1. Cloner le dépôt

```bash
git clone URL_DU_DEPOT
cd ai-infrastructure-copilot
```

### 2. Créer un environnement virtuel

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Installer les dépendances

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configurer Gemini

Copier le fichier d’exemple :

```bash
cp .env.example .env
```

Compléter ensuite `.env` avec une clé Gemini valide :

```dotenv
GEMINI_API_KEY=VOTRE_CLE
GEMINI_MODEL=gemini-3.8-flash
```

Le fichier `.env` ne doit jamais être ajouté à Git.

## Utilisation

```bash
python copilot_v0.py
```

Le programme affiche les données qui seront envoyées et demande une confirmation explicite avant l’appel à Gemini.


## API FastAPI

Démarrer le serveur depuis la racine du projet :

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

La documentation interactive est disponible sur <http://127.0.0.1:8000/docs>.

| Route | Rôle |
| --- | --- |
| `GET /health` | Vérifier que l’API répond. |
| `GET /metrics` | Consulter un instantané des données système. |
| `POST /diagnose` | Demander un diagnostic à Gemini. |

Exemple de corps pour `POST /diagnose` :

```json
{
  "confirm_external_send": true,
  "include_logs": false
}
```

`confirm_external_send` doit être `true` pour autoriser l’appel externe. Quand `include_logs` vaut `false`, les logs ne sont pas inclus dans le prompt envoyé à Gemini.

## Tests

Installer les dépendances de développement :

```bash
python -m pip install -r requirements-dev.txt
```

Lancer les tests depuis la racine du projet :

```bash
python -m pytest -q
```

Les tests simulent l’appel Gemini : ils vérifient le comportement de l’API sans envoyer de données et sans consommer de quota.


## Sécurité

- la clé API est conservée dans `.env` ;
- `.env` est ignoré par Git ;
- les données sont affichées avant leur envoi ;
- l’utilisateur doit confirmer l’appel ;
- le modèle reçoit uniquement des instructions de diagnostic ;
- aucune action corrective n’est exécutée automatiquement.

## Roadmap

- Phase 0 : script de diagnostic terminal
- Phase 1 : API FastAPI
- Phase 2 : surveillance continue et PostgreSQL
- Phase 3 : RAG documentaire avec Qdrant
- Phase 4 : mémoire des incidents avec Redis
- Phase 5 : dashboard
- Phase 6 : Docker et déploiement
- Phase 7 : Prometheus et Grafana
- Phase 8 : workflows et agents optionnels
