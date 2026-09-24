from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    cpu_percent: Mapped[float] = mapped_column(Float, nullable=False)

    memory_total_gb: Mapped[float] = mapped_column(Float, nullable=False)
    memory_used_gb: Mapped[float] = mapped_column(Float, nullable=False)
    memory_available_gb: Mapped[float] = mapped_column(Float, nullable=False)
    memory_percent: Mapped[float] = mapped_column(Float, nullable=False)

    disk_total_gb: Mapped[float] = mapped_column(Float, nullable=False)
    disk_used_gb: Mapped[float] = mapped_column(Float, nullable=False)
    disk_free_gb: Mapped[float] = mapped_column(Float, nullable=False)
    disk_percent: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
