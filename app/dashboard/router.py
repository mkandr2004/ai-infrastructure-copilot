"""Routes HTML du tableau de bord."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.core.config import PROJECT_ROOT


TEMPLATES_DIRECTORY = (
    PROJECT_ROOT
    / "app"
    / "dashboard"
    / "templates"
)

templates = Jinja2Templates(
    directory=TEMPLATES_DIRECTORY,
)

router = APIRouter(
    tags=["dashboard"],
)


@router.get(
    "/dashboard",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def dashboard_page(
    request: Request,
) -> HTMLResponse:
    """Affiche la page principale du dashboard."""

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "page_title": "AI Infrastructure Copilot",
        },
    )
