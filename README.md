# pr-label-semver

Use pull request labels to update semantic version tags.

- Labels `semver:major`, `semver:minor`, or `semver:patch` update the corresponding part of semantic version
- Defaults to `patch` if no label is specified
- Automatic tracking of floating major tag to latest tag, i.e. `v1` -> `v1.2.3`

## Quick Start

```yaml
name: Release Build

on:
  push:
    branches: [main]

concurrency:
  group: release-${{ github.repository }}
  cancel-in-progress: false

permissions:
  contents: write
  pull-requests: read

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - name: Bump and write version tag
        id: bump
        uses: faisal-memon/pr-label-semver@v0
        with:
          write-tag: "true"
          write-major-tag: "true"
          github-token: ${{ github.token }}
          ignore-labels: "dependencies"

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v3
        with:
          tag_name: ${{ steps.bump.outputs.new-tag }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

> [!NOTE]
> - Ensure `actions/checkout` uses `fetch-depth: 0`
> - Requires workflow permissions: `contents: write` to be able to write the semantic version tag
> - Requires `pull-requests: read` when `version-bump` is empty (PR-label resolution path)
> - Must configure workflow `concurrency` with `cancel-in-progress: false` to avoid tag collisions

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `github-token` | `""` | Token used to query PR labels. Required when `version-bump` is empty (or provide `GITHUB_TOKEN` env). |
| `ignore-labels` | `"dependencies"` | Comma-separated PR labels to ignore before resolving semver labels. Set empty to ignore nothing. |
| `tag-prefix` | `v` | Prefix to apply to tags (for example `v1.2.3`). |
| `version-bump` | `""` | Explicit bump override: `major`, `minor`, or `patch`. Useful for `workflow_dispatch` or manual override. |
| `write-major-tag` | `"false"` | When `true` and `write-tag` is `true`, moves and pushes floating major tag (for example `v1` or `v0`). |
| `write-tag` | `"true"` | When `true`, creates and pushes the computed tag to `origin`. If tag already exists, action fails and asks to enable workflow concurrency. |

## Outputs

- `new-tag`: computed next tag (for example `v1.4.2`)
- `previous-tag`: latest existing tag used as the bump source
- `version-bump-used`: resolved bump type actually applied

## How it works

The version always follows `major`.`minor`.`patch` format. Each time this action is triggered:

- Fetches the latest semantic-version tag matching the prefix (`vX.Y.Z`). If none exist, starts from `v0.0.0`
- If `version-bump` is provided, it is used directly
- Otherwise, the action checks labels (`semver:major`, `semver:minor`, `semver:patch`) on the PR associated with the commit
- If no matching label is found, it defaults to `patch`
- Selected part of tag is bumped


Ignored labels are filtered out before semver labels are evaluated. By default, the action ignores the `dependencies` label.
