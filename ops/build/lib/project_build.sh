#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "Source ops/build/lib/project_build.sh from a build wrapper."
  exit 1
fi

goat_require_file() {
  local path="$1"
  if [ ! -f "${path}" ]; then
    echo "Required file not found: ${path}"
    exit 1
  fi
}

goat_source_dotenv_if_present() {
  local dotenv_path="$1"
  if [ -f "${dotenv_path}" ]; then
    set -a
    # shellcheck disable=SC1090
    . "${dotenv_path}"
    set +a
  fi
}

goat_build_project() {
  PROJECT_DIR="${PROJECT_DIR:-$(cd "${REPO_ROOT}" && pwd)}"
  PYTHON_BIN="${PYTHON_BIN:-python3}"
  VENV_DIR="${VENV_DIR:-${PROJECT_DIR}/.venv}"
  FRONTEND_DIR="${FRONTEND_DIR:-${PROJECT_DIR}/frontend}"
  PYTHON_REQUIREMENTS="${PYTHON_REQUIREMENTS:-requirements.txt}"
  PRIMARY_DOTENV_PATH="${PRIMARY_DOTENV_PATH:-${PROJECT_DIR}/.env}"
  SECONDARY_DOTENV_PATH="${SECONDARY_DOTENV_PATH:-}"
  REQUIRE_SECONDARY_DOTENV="${REQUIRE_SECONDARY_DOTENV:-0}"
  QUICK="${QUICK:-0}"
  BUILD_LABEL="${BUILD_LABEL:-GOAT AI build}"

  if [ -z "${GOAT_DEPLOY_MODE:-}" ]; then
    echo "GOAT_DEPLOY_MODE must be set by the build wrapper."
    exit 1
  fi

  if [ "${REQUIRE_SECONDARY_DOTENV}" = "1" ]; then
    goat_require_file "${SECONDARY_DOTENV_PATH}"
  fi

  echo "${BUILD_LABEL} starting"
  echo "1. Load environment"
  goat_source_dotenv_if_present "${PRIMARY_DOTENV_PATH}"
  if [ -n "${SECONDARY_DOTENV_PATH}" ]; then
    goat_source_dotenv_if_present "${SECONDARY_DOTENV_PATH}"
  fi
  export GOAT_DEPLOY_MODE="${GOAT_DEPLOY_MODE}"

  echo "2. Python virtualenv and dependencies"
  if [ "${QUICK}" = "1" ]; then
    echo "[QUICK] Skipping Python venv and pip install"
    if [ ! -x "${VENV_DIR}/bin/python" ]; then
      echo "Venv not found at ${VENV_DIR}. Run a full build first."
      exit 1
    fi
  else
    if [ ! -x "${VENV_DIR}/bin/python" ]; then
      echo "Creating virtualenv at ${VENV_DIR}"
      "${PYTHON_BIN}" -m venv "${VENV_DIR}"
    fi
    "${VENV_DIR}/bin/pip" install --upgrade pip --quiet
    "${VENV_DIR}/bin/pip" install -r "${PROJECT_DIR}/${PYTHON_REQUIREMENTS}" --quiet
  fi

  echo "3. Frontend dependencies and build"
  (cd "${FRONTEND_DIR}" && npm ci --silent)
  (cd "${FRONTEND_DIR}" && npm run build)

  echo "4. Config validation"
  (
    cd "${PROJECT_DIR}" && \
    GOAT_DEPLOY_MODE="${GOAT_DEPLOY_MODE}" \
    "${VENV_DIR}/bin/python" -c "from goat_ai.config.settings import load_settings; settings = load_settings(); print(f'GOAT_DEPLOY_MODE={settings.deploy_mode} ({settings.deploy_mode_name})')"
  )

  echo ""
  echo "Build complete"
  echo "Frontend bundle: ${FRONTEND_DIR}/dist"
  echo "Python venv:     ${VENV_DIR}"
}
