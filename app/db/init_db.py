"""Création des tables PostgreSQL nécessaires à l'application."""

from app.db.database import Base, engine
from app.models.metric import MetricSnapshot


def init_db() -> None:
    """Crée les tables absentes dans PostgreSQL."""

    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()

    print("Initialisation PostgreSQL terminée.")
    print("Table disponible :", MetricSnapshot.__tablename__)
