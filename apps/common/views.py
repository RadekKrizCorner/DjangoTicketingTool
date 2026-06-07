"""Public non-API views."""

from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render


def home_page(request: HttpRequest) -> HttpResponse:
    """Render the public project homepage."""
    link_groups = [
        {
            "label": "Product",
            "links": [
                {
                    "label": "Workspace UI",
                    "href": "/ui/",
                    "description": (
                        "Open the React workspace for projects, tasks, notifications, and profiles."
                    ),
                    "kind": "ui",
                    "external": False,
                },
                {
                    "label": "Django Admin",
                    "href": "/admin/",
                    "description": "Manage operational data through Django administration.",
                    "kind": "admin",
                    "external": False,
                },
            ],
        },
        {
            "label": "API",
            "links": [
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
            ],
        },
        {
            "label": "Project",
            "links": [
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
            ],
        },
    ]
    if settings.PUBLIC_GRAFANA_URL:
        link_groups[0]["links"].append(
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
    links = []
    for index, link in enumerate(
        [link for group in link_groups for link in group["links"]],
        start=1,
    ):
        link["index"] = f"{index:02d}"
        links.append(link)
    return render(request, "common/home.html", {"links": links, "link_groups": link_groups})


def ui_page(_request: HttpRequest) -> HttpResponseRedirect:
    """Redirect local Django UI path to the configured frontend service."""
    return redirect(settings.PUBLIC_UI_URL)


def docs_page(_request: HttpRequest) -> HttpResponseRedirect:
    """Redirect local Django docs path to the configured documentation site."""
    return redirect(settings.PUBLIC_DOCUMENTATION_URL)
