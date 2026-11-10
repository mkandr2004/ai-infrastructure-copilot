"""Construction du contexte local d'investigation."""

from collections.abc import Sequence

from app.schemas.incident import IncidentRecord
from app.schemas.workflow import InvestigationFinding


def build_investigation_context(
    findings: Sequence[InvestigationFinding],
    similar_incidents: Sequence[IncidentRecord],
    *,
    history_points_analyzed: int,
) -> str:
    """Formate les résultats déterministes du workflow."""

    if (
        not findings
        and not similar_incidents
        and history_points_analyzed == 0
    ):
        return ""

    lines = [
        "CONTEXTE D'INVESTIGATION LOCAL :",
        (
            "Les constats suivants ont été calculés "
            "de manière déterministe."
        ),
        (
            "Les anciens incidents sont des références "
            "historiques et ne prouvent pas que le problème "
            "actuel possède la même cause."
        ),
        "",
        (
            "Nombre de mesures historiques analysées : "
            f"{history_points_analyzed}"
        ),
    ]

    if findings:
        lines.extend(
            [
                "",
                "CONSTATS DÉTERMINISTES",
            ]
        )

    for position, finding in enumerate(
        findings,
        start=1,
    ):
        lines.extend(
            [
                "",
                f"[Constat {position}]",
                f"Ressource : {finding.target.value}",
                f"Gravité : {finding.severity.value}",
                f"Titre : {finding.title}",
                f"Détails : {finding.details}",
                "Preuves :",
            ]
        )

        lines.extend(
            f"- {evidence}"
            for evidence in finding.evidence
        )

    if similar_incidents:
        lines.extend(
            [
                "",
                "INCIDENTS HISTORIQUES SIMILAIRES",
            ]
        )

    for position, incident in enumerate(
        similar_incidents,
        start=1,
    ):
        lines.extend(
            [
                "",
                f"[Incident historique {position}]",
                f"Identifiant : {incident.id}",
                (
                    "Date : "
                    f"{incident.created_at.isoformat()}"
                ),
                (
                    "Description signalée : "
                    f"{incident.problem_description}"
                ),
                (
                    "Métriques : "
                    f"CPU {incident.metrics.cpu_percent:.1f} %, "
                    f"mémoire "
                    f"{incident.metrics.memory_percent:.1f} %, "
                    f"disque "
                    f"{incident.metrics.disk_percent:.1f} %"
                ),
            ]
        )

    return "\n".join(lines)
