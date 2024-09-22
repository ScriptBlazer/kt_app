#!/bin/bash

set -e

python manage.py collectstatic --no-input --settings "${DJANGO_SETTINGS_MODULE}"

python "/app/docker/scripts/wait_for_postgres.py"

echo "Running migrations"
python manage.py migrate --settings "${DJANGO_SETTINGS_MODULE}"

gunicorn config.wsgi:application --preload --bind "0.0.0.0:8000" -n "kt_app" --workers="${WEB_CONCURRENCY:-1}"