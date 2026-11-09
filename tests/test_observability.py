from types import SimpleNamespace
from unittest.mock import patch

from fastapi import Request
from fastapi.testclient import TestClient

from app.main import app
from app.observability.middleware import (
    get_route_label,
)


client = TestClient(app)


def test_prometheus_endpoint_exposes_system_metrics():
    with patch(
        "app.observability.metrics.update_system_metrics",
    ) as mock_update:
        response = client.get(
            "/metrics/prometheus"
        )

    assert response.status_code == 200
    assert response.headers[
        "content-type"
    ].startswith("text/plain")

    assert (
        "ai_copilot_system_cpu_usage_percent"
        in response.text
    )
    assert (
        "ai_copilot_system_memory_usage_percent"
        in response.text
    )
    assert (
        "ai_copilot_system_disk_usage_percent"
        in response.text
    )

    mock_update.assert_called_once()


def test_prometheus_middleware_records_http_request():
    health_response = client.get("/health")

    assert health_response.status_code == 200

    metrics_response = client.get(
        "/metrics/prometheus"
    )

    matching_lines = [
        line
        for line in metrics_response.text.splitlines()
        if (
            line.startswith(
                "ai_copilot_http_requests_total"
            )
            and 'method="GET"' in line
            and 'route="/health"' in line
            and 'status_code="200"' in line
        )
    ]

    assert len(matching_lines) == 1


def test_route_label_uses_fastapi_template():
    request = Request(
        {
            "type": "http",
            "route": SimpleNamespace(
                path="/incidents/{incident_id}",
            ),
        }
    )

    assert get_route_label(request) == (
        "/incidents/{incident_id}"
    )


def test_route_label_handles_unmatched_request():
    request = Request(
        {
            "type": "http",
        }
    )

    assert get_route_label(request) == "unmatched"
