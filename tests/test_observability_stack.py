import json
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict:
    with path.open(
        encoding="utf-8",
    ) as yaml_file:
        return yaml.safe_load(yaml_file)


def test_prometheus_scrapes_fastapi_metrics():
    config = load_yaml(
        PROJECT_ROOT
        / "deploy"
        / "prometheus"
        / "prometheus.yml"
    )

    scrape_config = config["scrape_configs"][0]

    assert scrape_config["job_name"] == (
        "ai-infrastructure-copilot"
    )
    assert scrape_config["metrics_path"] == (
        "/metrics/prometheus"
    )
    assert scrape_config["static_configs"][0][
        "targets"
    ] == [
        "app:8000",
    ]


def test_grafana_datasource_targets_prometheus():
    config = load_yaml(
        PROJECT_ROOT
        / "deploy"
        / "grafana"
        / "provisioning"
        / "datasources"
        / "prometheus.yml"
    )

    datasource = config["datasources"][0]

    assert datasource["uid"] == "prometheus"
    assert datasource["type"] == "prometheus"
    assert datasource["url"] == (
        "http://prometheus:9090"
    )
    assert datasource["isDefault"] is True
    assert datasource["editable"] is False


def test_grafana_dashboard_uses_expected_metrics():
    dashboard_path = (
        PROJECT_ROOT
        / "deploy"
        / "grafana"
        / "dashboards"
        / "infrastructure-overview.json"
    )

    dashboard = json.loads(
        dashboard_path.read_text(
            encoding="utf-8",
        )
    )

    assert dashboard["uid"] == (
        "ai-infrastructure-copilot"
    )
    assert len(dashboard["panels"]) == 7

    expressions = [
        target["expr"]
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
    ]

    expected_metrics = [
        "up",
        "ai_copilot_system_cpu_usage_percent",
        "ai_copilot_system_memory_usage_percent",
        "ai_copilot_system_disk_usage_percent",
        "ai_copilot_http_requests_total",
        (
            "ai_copilot_http_request_"
            "duration_seconds_bucket"
        ),
    ]

    for metric_name in expected_metrics:
        assert any(
            metric_name in expression
            for expression in expressions
        )
