"""Instrumentation Prometheus des requêtes HTTP."""

from time import perf_counter

from fastapi import Request
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)
from starlette.responses import Response

from app.observability.metrics import (
    record_http_request,
)


def get_route_label(request: Request) -> str:
    """Retourne le modèle de route utilisé par FastAPI."""

    route = request.scope.get("route")
    route_path = getattr(route, "path", None)

    if isinstance(route_path, str):
        return route_path

    return "unmatched"


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Mesure le nombre et la durée des requêtes HTTP."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        started_at = perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code

            return response
        finally:
            duration_seconds = (
                perf_counter() - started_at
            )

            record_http_request(
                method=request.method,
                route=get_route_label(request),
                status_code=status_code,
                duration_seconds=duration_seconds,
            )
