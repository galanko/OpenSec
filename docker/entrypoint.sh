#!/usr/bin/env bash
set -euo pipefail

# OpenSec container entrypoint
# Ensures data directory exists, then starts supervisord.

DATA_DIR="${OPENSEC_DATA_DIR:-/data}"

echo "=== OpenSec ==="
echo "  Data dir:    $DATA_DIR"
echo "  App port:    ${OPENSEC_APP_PORT:-8000}"
echo "  Engine port: ${OPENSEC_OPENCODE_PORT:-4096}"
echo "  Engine bin:  ${OPENSEC_OPENCODE_BIN:-/app/bin/opencode}"
echo "==============="

# Ensure data directory exists
mkdir -p "$DATA_DIR"

# Start all services via supervisord
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/opensec.conf
