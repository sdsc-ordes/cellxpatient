#!/usr/bin/env bash
# shellcheck disable=SC1091
#
# Formatting.
set -euo pipefail

root_dir=$(git rev-parse --show-toplevel)
. "$root_dir/tools/ci/general.sh"

if command -v nix >/dev/null; then
    nix run --accept-flake-config "$root_dir/tools/nix#treefmt" -- "$@"
else
    ci::print_warning "Nix not found: formatting only Python using ruff and docs files with prettier."
    uv run ruff format
    npx --yes prettier --write --ignore-unknown "$root_dir"
fi
