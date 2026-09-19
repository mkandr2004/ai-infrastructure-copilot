# AI Infrastructure Copilot

AI Infrastructure Copilot est un projet personnel orienté AI Engineering, MLOps et observabilité.

Son objectif est de surveiller une infrastructure Linux, de collecter ses métriques et ses logs, puis d’utiliser un modèle d’intelligence artificielle pour générer des diagnostics prudents et structurés.

## État actuel

Phase 0 — MVP minimal de bout en bout terminé.

Le programme peut actuellement :

- collecter l’utilisation du CPU ;
- collecter l’utilisation de la mémoire RAM ;
- collecter l’espace disque ;
- récupérer les avertissements et erreurs avec `journalctl` ;
- structurer les données au format JSON ;
- construire un prompt de diagnostic ;
- demander une confirmation avant tout envoi ;
- appeler l’API Gemini ;
- afficher un diagnostic dans le terminal ;
- gérer les principales erreurs de configuration et d’API.

## Architecture actuelle

```text
Machine Linux
      ↓
psutil + journalctl
      ↓
Dictionnaire Python
      ↓
JSON
      ↓
Prompt structuré
      ↓
Gemini API
      ↓
Diagnostic dans le terminal
```

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
