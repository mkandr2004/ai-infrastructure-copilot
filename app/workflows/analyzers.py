"""Analyse déterministe des métriques d'infrastructure."""

from collections.abc import Sequence
from typing import Any

from app.schemas.workflow import (
    FindingSeverity,
    InvestigationFinding,
    InvestigationTarget,
)


WARNING_THRESHOLD = 80.0
CRITICAL_THRESHOLD = 90.0


def metric_history_values(
    history: Sequence[Any],
    attribute_name: str,
) -> list[float]:
    """Extrait les valeurs numériques d'un historique."""

    values: list[float] = []

    for snapshot in history:
        value = getattr(
            snapshot,
            attribute_name,
            None,
        )

        if isinstance(value, int | float):
            values.append(float(value))

    return values


def determine_severity(
    current_value: float,
    history_values: list[float],
) -> FindingSeverity:
    """Détermine la gravité selon la mesure et la moyenne."""

    reference_value = current_value

    if history_values:
        history_average = (
            sum(history_values) / len(history_values)
        )
        reference_value = max(
            current_value,
            history_average,
        )

    if reference_value >= CRITICAL_THRESHOLD:
        return FindingSeverity.CRITICAL

    if reference_value >= WARNING_THRESHOLD:
        return FindingSeverity.WARNING

    return FindingSeverity.INFO


def build_metric_finding(
    *,
    target: InvestigationTarget,
    label: str,
    current_value: float,
    history_values: list[float],
) -> InvestigationFinding:
    """Construit un constat structuré pour une ressource."""

    severity = determine_severity(
        current_value,
        history_values,
    )

    if severity == FindingSeverity.CRITICAL:
        title = f"{label} à un niveau critique"
        details = (
            f"L'utilisation actuelle ou la moyenne récente "
            f"de {label.lower()} atteint au moins "
            f"{CRITICAL_THRESHOLD:.0f} %."
        )
    elif severity == FindingSeverity.WARNING:
        title = f"{label} à surveiller"
        details = (
            f"L'utilisation actuelle ou la moyenne récente "
            f"de {label.lower()} atteint au moins "
            f"{WARNING_THRESHOLD:.0f} %."
        )
    else:
        title = f"{label} dans une plage normale"
        details = (
            f"Aucun dépassement des seuils de surveillance "
            f"n'est observé pour {label.lower()}."
        )

    evidence = [
        f"Valeur actuelle : {current_value:.1f} %",
    ]

    if history_values:
        history_average = (
            sum(history_values) / len(history_values)
        )
        history_maximum = max(history_values)

        evidence.extend(
            [
                (
                    "Moyenne historique : "
                    f"{history_average:.1f} %"
                ),
                (
                    "Maximum historique : "
                    f"{history_maximum:.1f} %"
                ),
                (
                    "Nombre de mesures historiques : "
                    f"{len(history_values)}"
                ),
            ]
        )

    return InvestigationFinding(
        target=target,
        severity=severity,
        title=title,
        details=details,
        evidence=evidence,
    )


def analyze_system_metrics(
    system_data: dict,
    history: Sequence[Any] = (),
) -> list[InvestigationFinding]:
    """Analyse CPU, mémoire et disque."""

    cpu_value = float(
        system_data["cpu"]["percent"]
    )
    memory_value = float(
        system_data["memory"]["percent"]
    )
    disk_value = float(
        system_data["disk"]["percent"]
    )

    return [
        build_metric_finding(
            target=InvestigationTarget.CPU,
            label="CPU",
            current_value=cpu_value,
            history_values=metric_history_values(
                history,
                "cpu_percent",
            ),
        ),
        build_metric_finding(
            target=InvestigationTarget.MEMORY,
            label="Mémoire",
            current_value=memory_value,
            history_values=metric_history_values(
                history,
                "memory_percent",
            ),
        ),
        build_metric_finding(
            target=InvestigationTarget.DISK,
            label="Disque",
            current_value=disk_value,
            history_values=metric_history_values(
                history,
                "disk_percent",
            ),
        ),
    ]
