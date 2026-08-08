#!/bin/sh
set -e
PORT="${PORT:-8080}"
echo "Starting gunicorn on 0.0.0.0:${PORT}"
exec gunicorn app:app --bind "0.0.0.0:${PORT}" --workers 1 --threads 4 --timeout 120
