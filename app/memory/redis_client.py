"""Connexion à la mémoire temporaire Redis."""

from redis import Redis

from app.core.config import Settings


def create_redis_client(
    settings: Settings,
) -> Redis:
    """Crée un client Redis configuré pour l'application."""

    password = None

    if settings.redis_password is not None:
        configured_password = (
            settings.redis_password
            .get_secret_value()
            .strip()
        )

        if configured_password:
            password = configured_password

    return Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=password,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def check_redis_connection(
    client: Redis,
) -> bool:
    """Vérifie que Redis répond."""

    return bool(client.ping())
