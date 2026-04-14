#!/usr/bin/env bash
# GOAT AI local Linux deploy.
# Usage:
#   bash ops/deploy/deploy.sh
#   QUICK=1 bash ops/deploy/deploy.sh
#   SKIP_BUILD=1 bash ops/deploy/deploy.sh
#   SYNC_GIT=1 bash ops/deploy/deploy.sh
#   RELEASE_BUNDLE=/tmp/goat-release.tar.gz RELEASE_MANIFEST=/tmp/release-manifest.json bash ops/deploy/deploy.sh

set -euo pipefail

_DEPLOY_SCRIPT="${BASH_SOURCE[0]:-$0}"
SCRIPT_DIR="$(cd "$(dirname "${_DEPLOY_SCRIPT}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd)}"
if [[ -f "$_DEPLOY_SCRIPT" ]]; then
  chmod +x "$_DEPLOY_SCRIPT" 2>/dev/null || true
fi
unset _DEPLOY_SCRIPT

GOAT_DEPLOY_MODE="${GOAT_DEPLOY_MODE:-0}"
if [ "${GOAT_DEPLOY_MODE}" != "0" ]; then
  echo "ops/deploy/deploy.sh is the local Linux deploy entrypoint and requires GOAT_DEPLOY_MODE=0."
  exit 1
fi

DEPLOY_LABEL="GOAT AI local Linux deploy"
GOAT_SYSTEMD_UNIT=""

source "${SCRIPT_DIR}/lib/backend_server_deploy.sh"

goat_backend_server_deploy
