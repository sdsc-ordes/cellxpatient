#!/usr/bin/env bash
# shellcheck disable=SC1091
#
# Rebuild frontend/dist only when needed
set -euo pipefail

root_dir=$(git rev-parse --show-toplevel)
frontend_dir="$root_dir/frontend"
output_dir="$root_dir/.output"
deps_hash_marker="$output_dir/frontend-deps-marker"
build_dist_marker="$output_dir/frontend-dist-marker"
force_build=0

. "$root_dir/tools/ci/general.sh"

mkdir -p "$output_dir"
cd "$frontend_dir"

if ! command -v npm >/dev/null; then
    ci::print_warning "'npm' not found, exiting."
    exit 0
fi

# First check if frontend dependencies changed
lock=$(git hash-object package-lock.json)
if [ ! -d node_modules ] || [ "$lock" != "$(cat "$deps_hash_marker" 2>/dev/null || true)" ]; then
    ci::print_info "Frontend dependencies changed, runing npm ci to rebuild them."
    npm ci
    echo "$lock" >"$deps_hash_marker"
    force_build=1
fi

# Re-build frontend if any file changed since last checked or deps changed
committed=$(git rev-parse HEAD:frontend)
if [ "$force_build" = 1 ] || [ ! -f dist/index.html ] ||
    [ "$committed" != "$(cat "$build_dist_marker" 2>/dev/null || true)" ]; then
    ci::print_info "Frontend changed, rebuilding dist…"
    npm run build
    echo "$committed" >"$build_dist_marker"
fi
