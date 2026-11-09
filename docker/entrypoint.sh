#!/bin/sh

set -eu

initialize_database="${INITIALIZE_DATABASE:-true}"
max_attempts="${DATABASE_INIT_MAX_ATTEMPTS:-30}"
retry_seconds="${DATABASE_INIT_RETRY_SECONDS:-2}"

if [ "$initialize_database" = "true" ]; then
    attempt=1

    while true; do
        echo "Initialisation PostgreSQL (tentative ${attempt}/${max_attempts})..."

        if python -m app.db.init_db; then
            break
        fi

        if [ "$attempt" -ge "$max_attempts" ]; then
            echo "PostgreSQL reste indisponible après ${max_attempts} tentatives." >&2
            exit 1
        fi

        attempt=$((attempt + 1))
        sleep "$retry_seconds"
    done
fi

exec "$@"
