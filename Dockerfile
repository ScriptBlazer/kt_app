FROM --platform=linux/amd64 python:3.11-slim AS builder-base

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.production

RUN apt update && \
    apt upgrade -y && \
    apt install -y --no-install-recommends curl && \
    apt clean  && \
    apt autoremove -y && \
    apt purge -y --auto-remove && \
    rm -rf /var/lib/apt/lists/* && \
    addgroup --system app && \
    adduser --system --group app


FROM builder-base AS python-base

# install os dependencies needed to compile python dependencies
RUN apt update && \
    apt install --no-install-recommends --yes --quiet  \
    build-essential software-properties-common \
    musl-dev gcc g++ libpq-dev libffi-dev git

# create virtual environment
RUN python3 -m venv /venv && \
    pip install --no-cache-dir --upgrade pip setuptools wheel

# install python dependencies
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM builder-base AS app-base

WORKDIR /app

# copy virtual environment
COPY --chown=app:app --from=python-base /venv /venv

# copy project
COPY  . .

# set ownership of app folder
RUN chown -R app:app /app

# run as app user
USER app:app

# expose ports for gunicorn
EXPOSE 8000

ENTRYPOINT [ "/app/docker/entrypoints/web.sh" ]