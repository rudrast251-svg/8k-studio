#!/usr/bin/env bash
# Build script for platforms like Render/Railway.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate
python manage.py seed_demo
