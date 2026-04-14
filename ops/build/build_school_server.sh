#!/usr/bin/env bash
# GOAT AI school Ubuntu build.
#
# Usage:
#   bash ops/build/build_school_server.sh
#   QUICK=1 bash ops/build/build_school_server.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PROJECT_DIR="${PROJECT_DIR:-${REPO_ROOT}}"
GOAT_DEPLOY_MODE="${GOAT_DEPLOY_MODE:-1}"

if [ "${GOAT_DEPLOY_MODE}" != "1" ]; then
  echo "ops/build/build_school_server.sh is the school-server build entrypoint and requires GOAT_DEPLOY_MODE=1."
  exit 1
fi

BUILD_LABEL="GOAT AI school server build"
PRIMARY_DOTENV_PATH="${PROJECT_DIR}/.env"
SECONDARY_DOTENV_PATH="${PROJECT_DIR}/.env.school-ubuntu"
REQUIRE_SECONDARY_DOTENV=1

source "${SCRIPT_DIR}/lib/project_build.sh"

goat_build_project
