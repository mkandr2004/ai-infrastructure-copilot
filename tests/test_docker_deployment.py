from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_compose_config() -> dict:
    compose_path = PROJECT_ROOT / "compose.yaml"

    with compose_path.open(
        encoding="utf-8",
    ) as compose_file:
        return yaml.safe_load(compose_file)


def test_compose_defines_required_services_and_volumes():
    compose = load_compose_config()
    services = compose["services"]

    assert set(services) == {
        "app",
        "monitoring",
        "postgres",
        "redis",
    }

    assert set(compose["volumes"]) == {
        "postgres_data",
        "qdrant_data",
        "redis_data",
    }

    assert services["postgres"]["image"] == (
        "postgres:17-alpine"
    )
    assert services["redis"]["image"] == (
        "redis:8-alpine"
    )


def test_compose_keeps_data_services_internal():
    services = load_compose_config()["services"]

    assert "ports" not in services["postgres"]
    assert "ports" not in services["redis"]
    assert services["app"]["ports"] == [
        "127.0.0.1:${APP_PORT:-8000}:8000"
    ]

    app_environment = services["app"]["environment"]

    assert app_environment["POSTGRES_HOST"] == "postgres"
    assert app_environment["REDIS_HOST"] == "redis"
    assert app_environment["QDRANT_PATH"] == (
        "/app/data/qdrant"
    )


def test_compose_waits_for_healthy_dependencies():
    services = load_compose_config()["services"]
    app_dependencies = services["app"]["depends_on"]

    assert app_dependencies["postgres"]["condition"] == (
        "service_healthy"
    )
    assert app_dependencies["redis"]["condition"] == (
        "service_healthy"
    )
    assert services["monitoring"]["depends_on"]["app"][
        "condition"
    ] == "service_healthy"

    assert "healthcheck" in services["postgres"]
    assert "healthcheck" in services["redis"]
    assert services["monitoring"]["healthcheck"] == {
        "disable": True,
    }


def test_runtime_container_is_hardened():
    dockerfile = (
        PROJECT_ROOT
        / "Dockerfile"
    ).read_text(encoding="utf-8")
    compose = load_compose_config()

    assert "FROM python:${PYTHON_VERSION}" in dockerfile
    assert "USER app" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "ENTRYPOINT" in dockerfile

    assert compose["services"]["app"]["read_only"] is True
    assert compose["services"]["monitoring"][
        "read_only"
    ] is True


def test_docker_context_excludes_secrets_and_local_data():
    ignored_entries = {
        line.strip()
        for line in (
            PROJECT_ROOT
            / ".dockerignore"
        ).read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    assert ".env" in ignored_entries
    assert ".venv" in ignored_entries
    assert ".git" in ignored_entries
    assert "data/qdrant" in ignored_entries


def test_container_entrypoint_executes_application_command():
    entrypoint = (
        PROJECT_ROOT
        / "docker"
        / "entrypoint.sh"
    ).read_text(encoding="utf-8")

    assert "python -m app.db.init_db" in entrypoint
    assert 'exec "$@"' in entrypoint
