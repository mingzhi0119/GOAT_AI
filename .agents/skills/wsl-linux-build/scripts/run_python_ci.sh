#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/../../../.." && pwd)}"
REQUIREMENTS_FILE="requirements-ci.txt"
VENV_PATH="${GOAT_WSL_PYTHON_VENV:-$HOME/.cache/goat-ai/wsl-python-ci}"
SKIP_INSTALL=0

usage() {
  cat <<'EOF' >&2
Usage:
  bash ./.agents/skills/wsl-linux-build/scripts/run_python_ci.sh [--requirements-file path] [--venv-path path] [--skip-install] -- <command> [args...]

Example:
  bash ./.agents/skills/wsl-linux-build/scripts/run_python_ci.sh -- python -m pytest __tests__/ops/test_observability_asset_contract.py -q
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --requirements-file)
      REQUIREMENTS_FILE="$2"
      shift 2
      ;;
    --venv-path)
      VENV_PATH="$2"
      shift 2
      ;;
    --skip-install)
      SKIP_INSTALL=1
      shift
      ;;
    --)
      shift
      break
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if [[ $# -eq 0 ]]; then
  usage
  exit 2
fi

mkdir -p "$(dirname "$VENV_PATH")"

if [[ ! -x "$VENV_PATH/bin/python" ]]; then
  python3 -m venv "$VENV_PATH"
fi

REQUIREMENTS_PATH="$REPO_ROOT/$REQUIREMENTS_FILE"
if [[ ! -f "$REQUIREMENTS_PATH" ]]; then
  echo "Requirements file not found: $REQUIREMENTS_PATH" >&2
  exit 1
fi

STAMP_PATH="$VENV_PATH/.requirements.sha256"
REQUIREMENTS_SHA="$(sha256sum "$REQUIREMENTS_PATH" | awk '{print $1}')"

if [[ "$SKIP_INSTALL" -ne 1 ]]; then
  CURRENT_SHA=""
  if [[ -f "$STAMP_PATH" ]]; then
    CURRENT_SHA="$(cat "$STAMP_PATH")"
  fi
  if [[ "$CURRENT_SHA" != "$REQUIREMENTS_SHA" ]]; then
    "$VENV_PATH/bin/python" -m pip install --upgrade pip
    "$VENV_PATH/bin/python" -m pip install -r "$REQUIREMENTS_PATH"
    printf '%s' "$REQUIREMENTS_SHA" > "$STAMP_PATH"
  fi
fi

cd "$REPO_ROOT"

COMMAND=( "$@" )
case "${COMMAND[0]}" in
  python|python3)
    COMMAND[0]="$VENV_PATH/bin/python"
    ;;
  pip|pip3)
    COMMAND[0]="$VENV_PATH/bin/pip"
    ;;
esac

exec "${COMMAND[@]}"
