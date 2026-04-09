#!/usr/bin/env bash
# Regenerate docs/openapi.json and docs/api.llm.yaml on Linux Python 3.14 (matches GitHub Actions).
# Run from WSL: bash scripts/wsl_api_contract_refresh.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"
export PYTHONPATH="${REPO_ROOT}"
export PATH="${HOME}/.local/bin:${PATH}"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
uv run --no-project --python 3.14 --with-requirements requirements-ci.txt python -m tools.regenerate_openapi_json
uv run --no-project --python 3.14 --with-requirements requirements-ci.txt python -m tools.generate_llm_api_yaml
uv run --no-project --python 3.14 --with-requirements requirements-ci.txt python -m tools.check_api_contract_sync
echo "OK: docs/openapi.json and docs/api.llm.yaml refreshed; contract check passed."
