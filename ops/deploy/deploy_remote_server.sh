#!/usr/bin/env bash
# GOAT AI remote backend deploy for the public Vercel + DuckDNS shape.
# Usage:
#   bash ops/deploy/deploy_remote_server.sh
#   QUICK=1 bash ops/deploy/deploy_remote_server.sh
#   SKIP_BUILD=1 bash ops/deploy/deploy_remote_server.sh
#   SYNC_GIT=1 bash ops/deploy/deploy_remote_server.sh

set -euo pipefail

_DEPLOY_SCRIPT="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "${_DEPLOY_SCRIPT}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
if [[ -f "$_DEPLOY_SCRIPT" ]]; then
  chmod +x "$_DEPLOY_SCRIPT" 2>/dev/null || true
fi
unset _DEPLOY_SCRIPT

GOAT_DEPLOY_MODE="${GOAT_DEPLOY_MODE:-2}"
if [ "${GOAT_DEPLOY_MODE}" != "2" ]; then
  echo "ops/deploy/deploy_remote_server.sh requires GOAT_DEPLOY_MODE=2."
  exit 1
fi

DEPLOY_LABEL="GOAT AI remote backend deploy"
GOAT_SYSTEMD_UNIT="${GOAT_SYSTEMD_UNIT:-goat-ai}"

source "${SCRIPT_DIR}/lib/backend_server_deploy.sh"

goat_backend_server_deploy
