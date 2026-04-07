#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DEFAULT_MESSAGE="chore: update project"
COMMIT_MESSAGE="${*:-$DEFAULT_MESSAGE}"

cd "${REPO_ROOT}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "❌ Not inside a git repository."
  exit 1
fi

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

EXCLUDES=(
  ".venv"
  ".venv/**"
  "**/.ipynb_checkpoints"
  "**/.ipynb_checkpoints/**"
  "chat_logs.db"
  "chat_logs.db-shm"
  "chat_logs.db-wal"
  "fastapi.pid"
  "logs.csv"
  "frontend/dist"
  "frontend/node_modules"
)

echo "📦 Staging changes on ${CURRENT_BRANCH}..."
git add -A

for pattern in "${EXCLUDES[@]}"; do
  git reset -q HEAD -- "${pattern}" 2>/dev/null || true
done

if git diff --cached --quiet; then
  echo "ℹ️ No commitable changes staged."
  exit 0
fi

echo "📝 Commit message: ${COMMIT_MESSAGE}"
git commit -m "${COMMIT_MESSAGE}"

echo "🚀 Pushing to origin/${CURRENT_BRANCH}..."
git push origin "${CURRENT_BRANCH}"

echo "✅ Done."
