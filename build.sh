#!/usr/bin/env bash
# Build script used by Render (or any host) to install deps, collect static
# files, and apply migrations before starting the app.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
