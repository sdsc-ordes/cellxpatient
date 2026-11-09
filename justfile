# Makes the recipe’s arguments available as shell positional parameters $1, $2…
set positional-arguments

# Run any recipe as "bash -cue <recipe>"
# (-c = run as command, -u = report error for unset variable, -e = stops at first failing command)
set shell := ["bash", "-cue"]

root_dir := `git rev-parse --show-toplevel`
flake_dir := root_dir / "tools/nix"
output_dir := root_dir / ".output"
build_dir := output_dir / "build"

# Import just modules
mod nix "./tools/just/nix.just"
mod changelog "./tools/just/changelog.just"

# Default target if you do not specify a target.
[group('general')]
default:
    just --list --unsorted

# Setup the project.
[group('general')]
setup *args:
    cd "{{root_dir}}" && ./tools/scripts/setup.sh

# Format the project.
[group('general')]
format *args:
    "{{root_dir}}/tools/scripts/setup-config-files.sh"
    "{{root_dir}}/tools/scripts/format.sh" "$@"

# Enter the default Nix development shell and execute the *args.
[group('nix')]
develop *args:
    just nix::develop "default" "$@"

# Run commands over the ci development shell.
[group('nix')]
ci *args:
    just nix::develop "ci" "$@"

# Run Cellxpatient CLI in dev mode
[group('cellxpatient')]
clxpt-dev *args:
    #!/usr/bin/env bash
    set -euo pipefail
    trap 'kill 0' EXIT
    (cd "{{root_dir}}/frontend" && npm run dev)&
    CELLXPATIENT_DEV=1 clxpt "$@"

# Install the React app
[group('cellxpatient')]
install-frontend *args:
    cd "{{root_dir}}/frontend" && npm ci && npm run build

# Build the frontend
[group('cellxpatient')]
build-frontend *args:
    cd "{{root_dir}}/frontend" && npm run build

# Re-build the frontend only if the current build is stale
[group('cellxpatient')]
rebuild-stale-frontend *args:
    "{{root_dir}}/tools/scripts/rebuild-frontend.sh"

# Lint the project.
[group('TODO')]
lint *args:
    echo "TODO: Not implemented"

# Build the module.
[group('TODO')]
build *args:
    echo "TODO: Not implemented"

# Test the project.
[group('TODO')]
test *args:
    echo "TODO: Not implemented"

# Run an executable.
[group('TODO')]
run *args:
    echo "TODO: Not implemented"
