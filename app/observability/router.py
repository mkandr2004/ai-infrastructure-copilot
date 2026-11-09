"""Route d’exposition des métriques Prometheus."""

from fastapi import APIRouter, Response

from app.observability.metrics import (
    render_prometheus_metrics,
)


router = APIRouter(
    tags=["observability"],
)


@router.get(
    "/metrics/prometheus",
    include_in_schema=False,
)
def prometheus_metrics() -> Response:
    """Expose les métriques au format Prometheus."""

    payload, content_type = (
        render_prometheus_metrics()
    )

    return Response(
        content=payload,
        media_type=content_type,
    )
