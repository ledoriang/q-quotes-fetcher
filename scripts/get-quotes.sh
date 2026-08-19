#!/usr/bin/env bash
# Desktop-friendly launcher for q-quotes-fetcher (Linux/macOS).
# Runs from wherever it lives, passing all arguments through.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v uv >/dev/null 2>&1; then
    echo "error: 'uv' not found on PATH. Install it from https://docs.astral.sh/uv/" >&2
    exit 1
fi

cd "$ROOT"
exec uv run get-passages "$@"