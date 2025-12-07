#!/usr/bin/env bash
set -e
cd menu_ingredientes
python manage.py collectstatic --noinput
python manage.py migrate --noinput
gunicorn menu_ingredientes.wsgi --log-file -
