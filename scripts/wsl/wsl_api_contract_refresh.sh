#!/usr/bin/env bash
# Regenerate docs/api/openapi.json and docs/api/api.llm.yaml on Linux Python 3.14 (matches GitHub Actions).
# Run from WSL: bash scripts/wsl/wsl_api_contract_refresh.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"
export PYTHONPATH="${REPO_ROOT}"
export PATH="${HOME}/.local/bin:${PATH}"
if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi
uv run --no-project --python 3.14 --with-requirements requirements-ci.txt python -m tools.contracts.regenerate_openapi_json
uv run --no-project --python 3.14 --with-requirements requirements-ci.txt python -m tools.contracts.generate_llm_api_yaml
uv run --no-project --python 3.14 --with-requirements requirements-ci.txt python -m tools.contracts.check_api_contract_sync
echo "OK: docs/api/openapi.json and docs/api/api.llm.yaml refreshed; contract check passed."
