from datetime import datetime
import subprocess
import os
from pathlib import Path

from app.collectors.system import collect_system_metrics
from app.core.config import get_settings
from app.services.diagnosis import (
    build_diagnostic_prompt,
    request_diagnostic,
    serialize_system_data,
)

from dotenv import load_dotenv
from google import genai

import psutil
import json




def display_system_metrics(metrics: dict) -> None:
    """Affiche les métriques et les logs dans un format lisible."""

    print("\nÉtat actuel de la machine")
    print("-" * 50)

    print(f"Date : {metrics['timestamp']}")

    print("\nCPU")
    print(f"  Utilisation : {metrics['cpu']['percent']} %")

    print("\nMémoire RAM")
    print(f"  Total       : {metrics['memory']['total_gb']} Go")
    print(f"  Utilisée    : {metrics['memory']['used_gb']} Go")
    print(f"  Disponible  : {metrics['memory']['available_gb']} Go")
    print(f"  Utilisation : {metrics['memory']['percent']} %")

    print("\nDisque")
    print(f"  Total       : {metrics['disk']['total_gb']} Go")
    print(f"  Utilisé     : {metrics['disk']['used_gb']} Go")
    print(f"  Libre       : {metrics['disk']['free_gb']} Go")
    print(f"  Utilisation : {metrics['disk']['percent']} %")

    print("\nLogs récents")

    for log in metrics["logs"]:
        print(f"  - {log}")

    print("-" * 50)



def main() -> None:
    print("Collecte des données système en cours...")

    system_data = collect_system_metrics()
    display_system_metrics(system_data)

    prompt = build_diagnostic_prompt(system_data)

    # Permet de vérifier exactement ce qui sera envoyé.
    print("\nPROMPT À ENVOYER")
    print("=" * 60)
    print(prompt)
    print("=" * 60)

    confirmation = input(
        "\nAprès vérification des données, envoyer à Google Gemini "
        "(consomme du quota et peut être facturé selon ton compte) ? "
        "Tape 'oui' : "
    )

    if confirmation.strip().lower() != "oui":
        print("Envoi annulé. Aucun appel à Gemini.")
        return

    print("\nAnalyse Gemini en cours...")

    try:
        diagnostic = request_diagnostic(prompt, get_settings())

    except ValueError as error:
        print(f"\nErreur de configuration : {error}")
        return

    except Exception as error:
        # Évite d'afficher une exception complète contenant
        # éventuellement des informations sensibles.
        print("\nL'appel à Gemini a échoué.")
        print(f"Type d'erreur : {type(error).__name__}")

        status = getattr(error, "status_code", None)

        if status is None:
            status = getattr(error, "code", None)

        if status is not None:
            print(f"Code d'erreur : {status}")

        print("Vérifie la connexion, la clé, le modèle et les quotas.")
        return

    print("\nDIAGNOSTIC IA")
    print("=" * 60)
    print(diagnostic)
    print("=" * 60)


if __name__ == "__main__":
    main()