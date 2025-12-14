#!/usr/bin/env bash

echo "Starting build process..."

# Install Python dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

echo "Build completed!"