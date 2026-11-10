from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.alerts.storage import alert_key, list_alerts, save_alert
from app.main import app
from app.schemas.alert import AlertRecord, AlertmanagerAlert


client = TestClient(app)


def make_settings():
    return SimpleNamespace(
        redis_key_prefix="test",
        alert_ttl_seconds=3600,
        alert_webhook_token=SecretStr("secret-test"),
        notification_webhook_url=None,
        notification_timeout_seconds=2.0,
    )


def make_alert(status: str = "firing") -> AlertmanagerAlert:
    return AlertmanagerAlert(
        status=status,
        labels={
            "alertname": "CPUHigh",
            "severity": "warning",
        },
        annotations={"summary": "CPU élevé"},
        startsAt="2026-11-10T12:00:00Z",
        endsAt=None,
        generatorURL="http://prometheus/graph",
        fingerprint="fingerprint-1",
    )


def make_record() -> AlertRecord:
    now = datetime.now(UTC)
    return AlertRecord(
        fingerprint="fingerprint-1",
        status="firing",
        labels={"alertname": "CPUHigh", "severity": "warning"},
        annotations={"summary": "CPU élevé"},
        starts_at=now,
        received_at=now,
    )


def webhook_payload() -> dict:
    return {
        "status": "firing",
        "receiver": "ai-copilot-api",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "CPUHigh",
                    "severity": "warning",
                },
                "annotations": {"summary": "CPU élevé"},
                "startsAt": "2026-11-10T12:00:00Z",
                "endsAt": "0001-01-01T00:00:00Z",
                "generatorURL": "http://prometheus/graph",
                "fingerprint": "fingerprint-1",
            }
        ],
    }


def test_alert_key_is_namespaced():
    assert alert_key(make_settings(), "abc") == "test:alert:abc"


def test_save_alert_writes_record_and_index():
    redis_client = MagicMock()
    pipeline = redis_client.pipeline.return_value.__enter__.return_value

    record = save_alert(redis_client, make_settings(), make_alert())

    assert record.fingerprint == "fingerprint-1"
    assert record.status == "firing"
    pipeline.set.assert_called_once()
    pipeline.zadd.assert_called_once()
    pipeline.expire.assert_called_once()
    pipeline.execute.assert_called_once_with()


def test_list_alerts_filters_status_and_removes_expired_ids():
    redis_client = MagicMock()
    record = make_record()
    redis_client.zrevrange.return_value = ["expired", "fingerprint-1"]
    redis_client.get.side_effect = [None, record.model_dump_json()]

    alerts = list_alerts(
        redis_client,
        make_settings(),
        status="firing",
    )

    assert alerts == [record]
    redis_client.zrem.assert_called_once_with(
        "test:alerts:index",
        "expired",
    )


def test_alert_webhook_rejects_invalid_token():
    with patch(
        "app.alerts.router.get_settings",
        return_value=make_settings(),
    ):
        response = client.post(
            "/alerts/webhook",
            json=webhook_payload(),
            headers={"Authorization": "Bearer incorrect"},
        )

    assert response.status_code == 401


def test_alert_webhook_persists_authenticated_alerts():
    redis_client = MagicMock()
    record = make_record()

    with (
        patch(
            "app.alerts.router.get_settings",
            return_value=make_settings(),
        ),
        patch(
            "app.alerts.router.create_redis_client",
            return_value=redis_client,
        ),
        patch(
            "app.alerts.router.save_alert",
            return_value=record,
        ) as mock_save,
        patch(
            "app.alerts.router.send_alert_notification",
            return_value=False,
        ),
    ):
        response = client.post(
            "/alerts/webhook",
            json=webhook_payload(),
            headers={"Authorization": "Bearer secret-test"},
        )

    assert response.status_code == 202
    assert response.json() == {
        "accepted": 1,
        "notification_sent": False,
        "notification_error": None,
    }
    mock_save.assert_called_once()
    redis_client.close.assert_called_once_with()


def test_alert_webhook_accepts_alert_when_notification_fails():
    redis_client = MagicMock()

    with (
        patch(
            "app.alerts.router.get_settings",
            return_value=make_settings(),
        ),
        patch(
            "app.alerts.router.create_redis_client",
            return_value=redis_client,
        ),
        patch(
            "app.alerts.router.save_alert",
            return_value=make_record(),
        ),
        patch(
            "app.alerts.router.send_alert_notification",
            side_effect=RuntimeError("webhook indisponible"),
        ),
    ):
        response = client.post(
            "/alerts/webhook",
            json=webhook_payload(),
            headers={"Authorization": "Bearer secret-test"},
        )

    assert response.status_code == 202
    assert response.json()["notification_error"] == "RuntimeError"


def test_list_alerts_endpoint_returns_records():
    redis_client = MagicMock()
    record = make_record()

    with (
        patch(
            "app.alerts.router.get_settings",
            return_value=make_settings(),
        ),
        patch(
            "app.alerts.router.create_redis_client",
            return_value=redis_client,
        ),
        patch(
            "app.alerts.router.list_alerts",
            return_value=[record],
        ) as mock_list,
    ):
        response = client.get(
            "/alerts",
            params={"limit": 5, "status": "firing"},
        )

    assert response.status_code == 200
    assert response.json()[0]["fingerprint"] == "fingerprint-1"
    assert mock_list.call_args.kwargs == {
        "limit": 5,
        "status": "firing",
    }
