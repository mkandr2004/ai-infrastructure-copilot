"""Définition et génération des métriques Prometheus."""

import psutil
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


HTTP_REQUESTS_TOTAL = Counter(
    "ai_copilot_http_requests_total",
    "Nombre total de requêtes HTTP traitées.",
    [
        "method",
        "route",
        "status_code",
    ],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "ai_copilot_http_request_duration_seconds",
    "Durée de traitement des requêtes HTTP.",
    [
        "method",
        "route",
    ],
    buckets=(
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
    ),
)

SYSTEM_CPU_USAGE_PERCENT = Gauge(
    "ai_copilot_system_cpu_usage_percent",
    "Pourcentage actuel d’utilisation du processeur.",
)

SYSTEM_MEMORY_USAGE_PERCENT = Gauge(
    "ai_copilot_system_memory_usage_percent",
    "Pourcentage actuel d’utilisation de la mémoire.",
)

SYSTEM_MEMORY_AVAILABLE_BYTES = Gauge(
    "ai_copilot_system_memory_available_bytes",
    "Quantité de mémoire actuellement disponible en octets.",
)

SYSTEM_DISK_USAGE_PERCENT = Gauge(
    "ai_copilot_system_disk_usage_percent",
    "Pourcentage actuel d’utilisation du disque.",
)

SYSTEM_DISK_FREE_BYTES = Gauge(
    "ai_copilot_system_disk_free_bytes",
    "Espace disque actuellement disponible en octets.",
)


def update_system_metrics() -> None:
    """Actualise les métriques système avant une collecte Prometheus."""

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    SYSTEM_CPU_USAGE_PERCENT.set(
        psutil.cpu_percent(interval=None)
    )
    SYSTEM_MEMORY_USAGE_PERCENT.set(
        memory.percent
    )
    SYSTEM_MEMORY_AVAILABLE_BYTES.set(
        memory.available
    )
    SYSTEM_DISK_USAGE_PERCENT.set(
        disk.percent
    )
    SYSTEM_DISK_FREE_BYTES.set(
        disk.free
    )


def record_http_request(
    method: str,
    route: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    """Enregistre une requête HTTP et sa durée."""

    HTTP_REQUESTS_TOTAL.labels(
        method=method,
        route=route,
        status_code=str(status_code),
    ).inc()

    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=method,
        route=route,
    ).observe(
        max(0.0, duration_seconds)
    )


def render_prometheus_metrics() -> tuple[bytes, str]:
    """Retourne toutes les métriques au format Prometheus."""

    update_system_metrics()

    return (
        generate_latest(),
        CONTENT_TYPE_LATEST,
    )
