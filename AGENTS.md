# AGENTS.md

## Purpose

`pr-label-semver` is a reusable GitHub composite action that computes the next semantic version tag based on:

- the latest existing Git tag
- an explicit bump input (`major`, `minor`, `patch`)
- or pull request labels (`semver:major`, `semver:minor`, `semver:patch`)

When no prior tags exist, it treats the baseline as `v0.0.0` (or `<tag-prefix>0.0.0`) and bumps from there.

## Core Behavior

The action runs `bump_semver.py` and emits:

- `new-tag`: the computed next version tag
- `previous-tag`: the latest version tag used as the bump source
- `version-bump-used`: the resolved bump type actually applied

By default, it computes outputs only.

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
- Keep the public action inputs stable when possible.
- Prefer pure-stdlib Python so the action stays lightweight on GitHub-hosted runners.

## Release Workflow Guardrails

- Release workflow resolves bump type from PR labels (`semver:major`, `semver:minor`, `semver:patch`) scoped to the target branch.
- The workflow defaults to `patch` when no semver label is present, and fails when more than one bump label is present.
- `.github/workflows/release_build.yaml` is the self-release workflow for this repo.
- It intentionally uses this action itself to dogfood behavior.
- It should keep workflow concurrency enabled to avoid tag collisions during releases.
