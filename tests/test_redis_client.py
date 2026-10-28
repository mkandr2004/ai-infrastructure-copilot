from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pydantic import SecretStr

from app.memory.redis_client import (
    check_redis_connection,
    create_redis_client,
)


def test_create_redis_client_uses_settings():
    settings = SimpleNamespace(
        redis_host="redis.test",
        redis_port=6380,
        redis_db=2,
        redis_password=SecretStr(""),
    )

    fake_client = MagicMock()

    with patch(
        "app.memory.redis_client.Redis",
        return_value=fake_client,
    ) as mock_redis:
        client = create_redis_client(settings)

    assert client is fake_client

    mock_redis.assert_called_once_with(
        host="redis.test",
        port=6380,
        db=2,
        password=None,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def test_check_redis_connection_returns_ping_result():
    fake_client = MagicMock()
    fake_client.ping.return_value = True

    result = check_redis_connection(
        fake_client,
    )

    assert result is True
    fake_client.ping.assert_called_once_with()
