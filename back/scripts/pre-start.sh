#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python -m app.pre_start

# Run migrations (temporarily disabled for debugging)
# alembic upgrade head
echo "Skipping migrations for now..."

# Start the main application
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app
