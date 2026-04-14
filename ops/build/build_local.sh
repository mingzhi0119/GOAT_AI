#!/usr/bin/env bash
# GOAT AI local Linux build.
#
# Usage:
#   bash ops/build/build_local.sh
#   QUICK=1 bash ops/build/build_local.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PROJECT_DIR="${PROJECT_DIR:-${REPO_ROOT}}"
GOAT_DEPLOY_MODE="${GOAT_DEPLOY_MODE:-0}"

if [ "${GOAT_DEPLOY_MODE}" != "0" ]; then
  echo "ops/build/build_local.sh is the local build entrypoint and requires GOAT_DEPLOY_MODE=0."
  exit 1
fi

BUILD_LABEL="GOAT AI local Linux build"
PRIMARY_DOTENV_PATH="${PROJECT_DIR}/.env"

source "${SCRIPT_DIR}/lib/project_build.sh"

goat_build_project
