## Development Guide

This guide documents how to set up the project for development and our
conventions, and is here to cover maintenance tasks such as pull/merge-requests,
continuous integration and releasing.

### Project setup

After installing the tools (see the README), run once per clone:

```bash
just setup
```

This sets up the git hooks and links the shared configuration files, such as the
formatter configuration, to the project root. See `tools/scripts/setup.sh` for
details.

### Formatting

`just format` formats the project. With Nix, it runs treefmt with all configured
formatters and accepts CLI arguments. Without Nix, it runs only Ruff and
Prettier, on the whole project. CLI arguments are ignored.

### Frontend

The CLI serves the built frontend from `frontend/dist`. After any change to the
frontend, it needs to be rebuild. This can be done manually with:

```bash
cd frontend
npm ci                # if needed, e.g. change in package.json
npm run build
```

During development, to automatically have any frontend change dynamically
updated in the deployed app without having to rebuild, the cellxpatient CLI is
available using the following just recipe:

```bash
just clxpt-dev <command> <args>
```

This is relevant only for commands that deploy the React app (e.g. `serve` and
`build` without the `--build-only` option`)

Additionally, to ensure that running the CLI always uses a matching frontend
version, there are git hooks to automatically rebuild `frontend/dist` to match
the latest commit of the currently checked-out branch. See the
[git hooks](#git-hooks) section for more information.

### Git Hooks

The git hooks are defined in `.githooks/` and use plain git to run, no extra
tool is required. They are enabled by `just setup`.

Currently there are two main suites executed by hooks:

- formatting: Formats the staged files (pre-commit)
- Frontend (re-)build: Rebuild `frontend/dist` if the committed frontend changed
  (post-commit/post-merge/post-checkout)

If formatting changes a file, the commit is stopped. Review the changes, stage
them with git add and commit again.

### Commit Convention

We use the
[conventional commits](https://www.conventionalcommits.org/en/v1.0.0/)
specification for commit messages and pull/merge-request titles.

<!-- Additional 'scopes' should be described here.-->
<!-- ### Scopes -->
