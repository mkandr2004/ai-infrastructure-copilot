from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.monitoring import collect_and_save, run_monitoring


def test_collect_and_save_without_logs():
    fake_metrics = {
        "timestamp": "2026-09-23T12:00:00+00:00",
        "cpu": {"percent": 10.0},
        "memory": {"percent": 20.0},
        "disk": {"percent": 30.0},
        "logs": [],
    }

    fake_snapshot = SimpleNamespace(
        id=99,
        collected_at="2026-09-23T12:00:00+00:00",
        cpu_percent=10.0,
        memory_percent=20.0,
        disk_percent=30.0,
    )

    fake_session = MagicMock()
    fake_session_context = MagicMock()
    fake_session_context.__enter__.return_value = fake_session

    with (
        patch(
            "app.monitoring.collect_system_metrics",
            return_value=fake_metrics,
        ) as mock_collect,
        patch(
            "app.monitoring.SessionLocal",
            return_value=fake_session_context,
        ) as mock_session_factory,
        patch(
            "app.monitoring.save_metric_snapshot",
            return_value=fake_snapshot,
        ) as mock_save,
    ):
        collect_and_save()

    mock_collect.assert_called_once_with(include_logs=False)
    mock_session_factory.assert_called_once_with()
    mock_save.assert_called_once_with(
        fake_session,
        fake_metrics,
    )


def test_monitoring_rejects_invalid_interval():
    with pytest.raises(
        ValueError,
        match="au moins une seconde",
    ):
        run_monitoring(0)


def test_monitoring_retries_after_error_and_stops_cleanly(capsys):
    with (
        patch(
            "app.monitoring.collect_and_save",
            side_effect=[
                RuntimeError("base indisponible"),
                KeyboardInterrupt(),
            ],
        ) as mock_collect,
        patch(
            "app.monitoring.time.monotonic",
            side_effect=[10.0, 11.0, 15.0],
        ),
        patch(
            "app.monitoring.time.sleep",
        ) as mock_sleep,
    ):
        run_monitoring(5)

    assert mock_collect.call_count == 2
    mock_sleep.assert_called_once_with(4.0)

    output = capsys.readouterr().out

    assert "RuntimeError" in output
    assert "nouvelle tentative" in output
    assert "arrêtée proprement" in output
