from types import SimpleNamespace

from app.schemas.workflow import (
    FindingSeverity,
    InvestigationTarget,
)
from app.workflows.analyzers import (
    analyze_system_metrics,
    determine_severity,
    metric_history_values,
)


def make_system_data(
    *,
    cpu: float = 20.0,
    memory: float = 30.0,
    disk: float = 40.0,
) -> dict:
    return {
        "cpu": {"percent": cpu},
        "memory": {"percent": memory},
        "disk": {"percent": disk},
    }


def test_normal_metrics_produce_information_findings():
    findings = analyze_system_metrics(
        make_system_data()
    )

    assert len(findings) == 3

    assert {
        finding.target
        for finding in findings
    } == {
        InvestigationTarget.CPU,
        InvestigationTarget.MEMORY,
        InvestigationTarget.DISK,
    }

    assert all(
        finding.severity == FindingSeverity.INFO
        for finding in findings
    )


def test_current_metrics_use_warning_and_critical_thresholds():
    findings = analyze_system_metrics(
        make_system_data(
            cpu=95.0,
            memory=85.0,
            disk=70.0,
        )
    )

    severities = {
        finding.target: finding.severity
        for finding in findings
    }

    assert severities[InvestigationTarget.CPU] == (
        FindingSeverity.CRITICAL
    )
    assert severities[InvestigationTarget.MEMORY] == (
        FindingSeverity.WARNING
    )
    assert severities[InvestigationTarget.DISK] == (
        FindingSeverity.INFO
    )


def test_history_average_can_raise_severity():
    history = [
        SimpleNamespace(
            cpu_percent=95.0,
            memory_percent=20.0,
            disk_percent=30.0,
        ),
        SimpleNamespace(
            cpu_percent=93.0,
            memory_percent=25.0,
            disk_percent=35.0,
        ),
    ]

    findings = analyze_system_metrics(
        make_system_data(cpu=10.0),
        history,
    )

    cpu_finding = next(
        finding
        for finding in findings
        if finding.target == InvestigationTarget.CPU
    )

    assert cpu_finding.severity == (
        FindingSeverity.CRITICAL
    )
    assert (
        "Moyenne historique : 94.0 %"
        in cpu_finding.evidence
    )
    assert (
        "Nombre de mesures historiques : 2"
        in cpu_finding.evidence
    )


def test_history_extraction_ignores_missing_values():
    history = [
        SimpleNamespace(cpu_percent=50.0),
        SimpleNamespace(memory_percent=60.0),
        SimpleNamespace(cpu_percent=None),
    ]

    values = metric_history_values(
        history,
        "cpu_percent",
    )

    assert values == [50.0]


def test_severity_boundaries_are_explicit():
    assert determine_severity(
        79.9,
        [],
    ) == FindingSeverity.INFO

    assert determine_severity(
        80.0,
        [],
    ) == FindingSeverity.WARNING

    assert determine_severity(
        90.0,
        [],
    ) == FindingSeverity.CRITICAL
