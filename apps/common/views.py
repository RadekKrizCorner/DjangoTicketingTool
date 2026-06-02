"""Public non-API views."""

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render


def home_page(request: HttpRequest) -> HttpResponse:
    """Render the public project homepage."""
    links = [
        {
            "label": "Swagger API Docs",
            "href": "/api/v1/docs/",
            "description": "Explore and test the REST API in the browser.",
            "kind": "api",
            "external": False,
        },
        {
            "label": "ReDoc",
            "href": "/api/v1/redoc/",
            "description": "Read the API contract in a structured reference view.",
            "kind": "api",
            "external": False,
        },
        {
            "label": "OpenAPI Schema",
            "href": "/api/v1/schema/",
            "description": "Download the machine-readable API schema.",
            "kind": "schema",
            "external": False,
        },
        {
            "label": "MkDocs",
            "href": "/docs/",
            "description": "Open architecture, deployment, and product documentation.",
            "kind": "docs",
            "external": False,
        },
        {
            "label": "GitHub",
            "href": "https://github.com/RadekKrizCorner/DjangoTicketingTool",
            "description": "View the source code and milestone history.",
            "kind": "source",
            "external": True,
        },
        {
            "label": "LinkedIn",
            "href": "https://www.linkedin.com/in/radekkriz/",
            "description": "Open Radek Kriz's professional profile.",
            "kind": "profile",
            "external": True,
        },
        {
            "label": "Django Admin",
            "href": "/admin/",
            "description": "Manage operational data through Django administration.",
            "kind": "admin",
            "external": False,
        },
    ]
    if settings.PUBLIC_GRAFANA_URL:
        links.append(
            {
                "label": "Grafana Monitoring",
                "href": settings.PUBLIC_GRAFANA_URL,
                "description": (
                    "Protected dashboards for API, database, async jobs, and host health."
                ),
                "kind": "monitoring",
                "external": True,
            }
        )
    return render(request, "common/home.html", {"links": links})


def docs_page(_request: HttpRequest) -> HttpResponseRedirect:
    """Redirect local Django docs path to the configured documentation site."""
    return redirect(settings.PUBLIC_DOCUMENTATION_URL)
