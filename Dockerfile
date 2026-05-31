FROM python:3.12-slim AS base

ENV DJANGO_SETTINGS_MODULE=config.settings.production
ENV PATH="/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

FROM base AS development

RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential curl libpq-dev \
  && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
COPY apps /app/apps
COPY config /app/config
RUN python -m venv /venv \
  && pip install --upgrade pip \
  && pip install ".[dev]"

COPY . /app/

FROM base AS build

RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential libpq-dev \
  && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml /app/
COPY apps /app/apps
COPY config /app/config
RUN python -m venv /venv \
  && pip install --upgrade pip \
  && pip install .

FROM base AS runtime

RUN apt-get update \
  && apt-get install -y --no-install-recommends curl \
  && rm -rf /var/lib/apt/lists/*

COPY --from=build /venv /venv
COPY apps /app/apps
COPY config /app/config
COPY manage.py /app/manage.py
RUN mkdir -p /app/staticfiles /app/media \
  && DJANGO_SECRET_KEY=build-time-static-secret \
    DJANGO_ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -fsS -H "Host: ${DJANGO_HEALTHCHECK_HOST:-localhost}" \
    http://127.0.0.1:8000/api/v1/health/live/ || exit 1

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
