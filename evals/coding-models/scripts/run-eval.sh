#!/usr/bin/env bash
# Thin wrapper around `python -m harness.runner`.
# Usage: ./scripts/run-eval.sh configs/mock.yaml [--quiet]
set -euo pipefail

cd "$(dirname "$0")/.."

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <config-yaml> [--quiet]" >&2
  exit 64
fi

exec python -m harness.runner --config "$@"
