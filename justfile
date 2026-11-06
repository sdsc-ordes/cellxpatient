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
default:
    just --list --unsorted

# Enter the default Nix development shell and execute the command `"$@"`.
develop *args:
    just nix::develop "default" "$@"

# Format the project.
format *args:
    "{{root_dir}}/tools/scripts/setup-config-files.sh"
    nix run --accept-flake-config {{flake_dir}}#treefmt -- "$@"

# Setup the project.
setup *args:
    cd "{{root_dir}}" && ./tools/scripts/setup.sh

# Run commands over the ci development shell.
ci *args:
    just nix::develop "ci" "$@"

# Cellxpatient dev mode recipes
[group('cellxpatient')]
clxpt-dev *args:
    #!/usr/bin/env bash
    set -euo pipefail
    trap 'kill 0' EXIT
    (cd "{{root_dir}}/frontend" && npm run dev)&
    CELLXPATIENT_DEV=1 clxpt "$@"

build-frontend *args:
    cd "{{root_dir}}/frontend" && npm run build

rebuild-stale-frontend *args:
    "{{root_dir}}/tools/scripts/rebuild-frontend.sh"

# Lint the project.
[group('general')]
lint *args:
    echo "TODO: Not implemented"

# Build the module.
[group('general')]
build *args:
    echo "TODO: Not implemented"

# Test the project.
[group('general')]
test *args:
    echo "TODO: Not implemented"

# Run an executable.
[group('general')]
run *args:
    echo "TODO: Not implemented"
