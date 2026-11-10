#!/bin/sh
set -eu

if [ -z "${ALERT_WEBHOOK_TOKEN:-}" ]; then
    echo "ALERT_WEBHOOK_TOKEN doit être défini." >&2
    exit 1
fi

escaped_token=$(printf '%s' "$ALERT_WEBHOOK_TOKEN" | sed 's/[\/&]/\\&/g')
sed "s/__ALERT_WEBHOOK_TOKEN__/$escaped_token/g" \
    /etc/alertmanager/alertmanager.yml.template \
    > /tmp/alertmanager.yml

exec /bin/alertmanager \
    --config.file=/tmp/alertmanager.yml \
    --storage.path=/alertmanager
