"""Surveillance périodique des métriques système."""

import argparse
import time

from app.collectors.system import collect_system_metrics
from app.db.database import SessionLocal
from app.services.metrics import save_metric_snapshot


def collect_and_save() -> None:
    """Collecte une mesure et l'enregistre dans PostgreSQL."""

    metrics = collect_system_metrics(include_logs=False)

    with SessionLocal() as session:
        snapshot = save_metric_snapshot(session, metrics)

    print("Instantané enregistré")
    print("ID :", snapshot.id)
    print("Date collectée :", snapshot.collected_at)
    print("CPU :", snapshot.cpu_percent)
    print("Mémoire :", snapshot.memory_percent)
    print("Disque :", snapshot.disk_percent)


def run_monitoring(interval_seconds: int) -> None:
    """Enregistre régulièrement les métriques jusqu'à l'arrêt manuel."""

    if interval_seconds < 1:
        raise ValueError(
            "L'intervalle doit être d'au moins une seconde."
        )

    print(
        f"Surveillance démarrée : une collecte toutes les "
        f"{interval_seconds} secondes."
    )
    print("Appuie sur Ctrl+C pour arrêter.")

    try:
        while True:
            cycle_started_at = time.monotonic()

            try:
                collect_and_save()
            except Exception as error:
                print(
                    "Échec d'un cycle :",
                    type(error).__name__,
                )
                print("Une nouvelle tentative sera effectuée.")

            elapsed_seconds = time.monotonic() - cycle_started_at
            remaining_seconds = max(
                0,
                interval_seconds - elapsed_seconds,
            )

            time.sleep(remaining_seconds)

    except KeyboardInterrupt:
        print("\nSurveillance arrêtée proprement.")


def main() -> None:
    """Lit la commande saisie et choisit le mode d'exécution."""

    parser = argparse.ArgumentParser(
        description="Collecte et enregistre les métriques système."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help=(
            "Nombre de secondes entre les collectes. "
            "Sans cette option, une seule mesure est enregistrée."
        ),
    )

    arguments = parser.parse_args()

    if arguments.interval is None:
        collect_and_save()
    else:
        run_monitoring(arguments.interval)


if __name__ == "__main__":
    main()
