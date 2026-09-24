from unittest.mock import patch

from app.db.init_db import Base, engine, init_db


def test_init_db_creates_registered_tables():
    assert "metric_snapshots" in Base.metadata.tables

    with patch.object(
        Base.metadata,
        "create_all",
    ) as mock_create_all:
        init_db()

    mock_create_all.assert_called_once_with(
        bind=engine,
    )
