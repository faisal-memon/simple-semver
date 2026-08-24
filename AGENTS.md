# AGENTS.md

## Purpose

`pr-label-semver` is a reusable GitHub composite action that computes the next semantic version tag based on:

- the latest existing Git tag
- an explicit bump input (`major`, `minor`, `patch`)
- or pull request labels (`semver:major`, `semver:minor`, `semver:patch`)

When no prior tags exist, it treats the baseline as `v0.0.0` (or `<tag-prefix>0.0.0`) and bumps from there.

## Core Behavior

The action runs `main.py` directly and emits:

- `new-tag`: the computed next version tag
- `previous-tag`: the latest version tag used as the bump source
- `version-bump-used`: the resolved bump type actually applied

By default, it computes outputs only.

## Module Layout

- `main.py` is the action entry point and orchestrates configuration, bump resolution, tag selection, writing, and outputs.
- `config.py` reads and validates action inputs and GitHub environment values. Its explicit bump field is `version_bump_override`.
- `git_ops.py` owns Git and GitHub operations. `Git.get_pull_request_labels(...)` is the boundary for finding the relevant PR and its labels.
- `pr_labels.py` contains only label parsing and bump-resolution rules.
- `semver.py` contains pure semantic-version tag filtering and bumping logic.
- `errors.py` provides the shared `ActionError` exception.

## Label Rules

- Only namespaced PR labels are recognized: `semver:major`, `semver:minor`, and `semver:patch`.
- Plain `major`, `minor`, and `patch` PR labels are intentionally unsupported.
- `ignore-labels` defaults to `dependencies`; callers can provide a comma-separated replacement or an empty value to disable ignored labels.

## Tag Writing Behavior

To avoid unexpected version reuse, tag creation is optimistic and strict:

1. fetch tags
2. compute the next version from the latest semantic-version tag
3. create the candidate tag locally
4. push the tag to `origin`

If the push reports the tag already exists, the action fails and tells callers to enable workflow concurrency with `cancel-in-progress: false`.

When `write-major-tag` is enabled, the action also force-updates the floating major tag for the computed major version (for example `v1` or `v0`).

## Maintainer Notes

- `Makefile` is the local developer entry point for validation.
- `make lint` checks Python syntax for the action and tests.
- `make test` runs the unit test suite.
- Tests are split by responsibility: `tests/test_config.py`, `tests/test_pr_labels.py`, and `tests/test_semver.py`.
- Keep the public action inputs stable when possible.
- Prefer pure-stdlib Python so the action stays lightweight on GitHub-hosted runners.

## Release Workflow Guardrails

- Release workflow resolves bump type from PR labels (`semver:major`, `semver:minor`, `semver:patch`) scoped to the target branch.
- The workflow defaults to `patch` when no semver label is present, and fails when more than one bump label is present.
- `.github/workflows/release_build.yaml` is the self-release workflow for this repo.
- It intentionally uses this action itself to dogfood behavior.
- It should keep workflow concurrency enabled to avoid tag collisions during releases.
