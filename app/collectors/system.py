from datetime import UTC, datetime
import subprocess

import psutil

def bytes_to_gb(value_in_bytes: int) -> float:
    """Convertit une quantité d'octets en gigaoctets."""

    value_in_gb = value_in_bytes / (1024 ** 3)
    return round(value_in_gb, 2)


def collect_system_logs(limit: int = 10) -> list[str]:
    """Récupère les derniers avertissements et erreurs de journalctl."""

    command = [
        "journalctl",
        "-p",
        "warning",
        "-n",
        str(limit),
        "--no-pager",
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        if result.returncode != 0:
            error_message = result.stderr.strip()

            return [
                f"Impossible de récupérer les logs : {error_message}"
            ]

        logs = [
            line
            for line in result.stdout.splitlines()
            if line.strip() and line.strip() != "-- No entries --"
        ]

        if not logs:
            return ["Aucun avertissement ou erreur récent."]

        return logs

    except FileNotFoundError:
        return ["La commande journalctl est introuvable."]

    except subprocess.TimeoutExpired:
        return ["La récupération des logs a dépassé 5 secondes."]


def collect_system_metrics(include_logs: bool = True) -> dict:
    """Collecte les principales métriques de la machine."""

    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    return {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "cpu": {
            "percent": cpu_percent,
        },
        "memory": {
            "total_gb": bytes_to_gb(memory.total),
            "used_gb": bytes_to_gb(memory.used),
            "available_gb": bytes_to_gb(memory.available),
            "percent": memory.percent,
        },
        "disk": {
            "total_gb": bytes_to_gb(disk.total),
            "used_gb": bytes_to_gb(disk.used),
            "free_gb": bytes_to_gb(disk.free),
            "percent": disk.percent,
        },
        "logs": collect_system_logs(limit=10) if include_logs else [],
    }
