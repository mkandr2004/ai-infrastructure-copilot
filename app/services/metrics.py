from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.metric import MetricSnapshot


def save_metric_snapshot(
    session: Session,
    metrics: dict,
) -> MetricSnapshot:
    snapshot = MetricSnapshot(
        collected_at=datetime.fromisoformat(metrics["timestamp"]),
        cpu_percent=metrics["cpu"]["percent"],
        memory_total_gb=metrics["memory"]["total_gb"],
        memory_used_gb=metrics["memory"]["used_gb"],
        memory_available_gb=metrics["memory"]["available_gb"],
        memory_percent=metrics["memory"]["percent"],
        disk_total_gb=metrics["disk"]["total_gb"],
        disk_used_gb=metrics["disk"]["used_gb"],
        disk_free_gb=metrics["disk"]["free_gb"],
        disk_percent=metrics["disk"]["percent"],
    )

    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)

    return snapshot


def list_metric_snapshots(
    session: Session,
    limit: int = 100,
) -> list[MetricSnapshot]:
    statement = (
        select(MetricSnapshot)
        .order_by(MetricSnapshot.collected_at.desc())
        .limit(limit)
    )

    return list(session.scalars(statement))