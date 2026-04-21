#!/bin/bash
set -euo pipefail

# Wait for nginx-test to be serving
echo "[playwright] waiting for nginx-test..."
until wget -qO- http://nginx-test/health >/dev/null 2>&1; do
  sleep 1
done
echo "[playwright] nginx-test is up"

# Wait for api-test via nginx
echo "[playwright] waiting for api-test..."
until wget -qO- http://nginx-test/api/health >/dev/null 2>&1; do
  sleep 1
done
echo "[playwright] api-test is up"

exec "$@"
