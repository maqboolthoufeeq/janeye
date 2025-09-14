#!/bin/bash
set -e

# If the first argument is 'celery', use the full path
if [ "$1" = "celery" ]; then
    shift  # Remove 'celery' from arguments
    exec /app/.venv/bin/celery "$@"
else
    # Otherwise execute the command as-is
    exec "$@"
fi
