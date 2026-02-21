#!/usr/bin/env bash
set -euo pipefail

echo "Running deployment security guardrails..."

if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo "ERROR: .env is tracked by git. Remove it from version control immediately."
  exit 1
fi

if [[ ! -f .dockerignore ]]; then
  echo "ERROR: .dockerignore is missing."
  exit 1
fi

if ! grep -qxF '.env' .dockerignore; then
  echo "ERROR: .dockerignore must contain '.env'."
  exit 1
fi

if ! grep -qxF '.env.*' .dockerignore; then
  echo "ERROR: .dockerignore must contain '.env.*'."
  exit 1
fi

if [[ ! -f docs/security/deployment-model.md ]]; then
  echo "ERROR: docs/security/deployment-model.md is missing."
  exit 1
fi

echo "Deployment security guardrails passed."
