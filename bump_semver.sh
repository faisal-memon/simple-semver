#!/usr/bin/env bash
set -euo pipefail

version_bump="${INPUT_VERSION_BUMP:-}"
tag_prefix="${INPUT_TAG_PREFIX:-v}"
github_token="${INPUT_GITHUB_TOKEN:-${GITHUB_TOKEN:-}}"
ignore_labels="${INPUT_IGNORE_LABELS:-dependencies}"
write_tag="${INPUT_WRITE_TAG:-false}"
write_major_tag="${INPUT_WRITE_MAJOR_TAG:-false}"

main() {
  version_bump="$(compute_version_bump)"
  previous_tag=""
  new_tag=""
  git fetch --tags --force >/dev/null 2>&1 || true
  latest_tag="$(resolve_latest_semver_tag)"
  validate_latest_tag_format "${latest_tag}"
  previous_tag="${tag_prefix}${latest_tag}"
  next_version="$(bump_from_previous "${latest_tag}" "${version_bump}")"
  new_tag="${tag_prefix}${next_version}"
  log_info "Resolved bump=${version_bump} from previous=${previous_tag} to new=${new_tag}"

  if [[ "${write_tag}" == "true" ]]; then
    log_info "write-tag=true; creating and pushing ${new_tag}"
    push_err_file="$(mktemp)"
    trap 'rm -f "${push_err_file}"' EXIT

    if git rev-parse -q --verify "refs/tags/${new_tag}" >/dev/null 2>&1; then
      git tag -d "${new_tag}" >/dev/null 2>&1 || true
    fi

    git tag "${new_tag}"

    if ! git push origin "refs/tags/${new_tag}" >"${push_err_file}" 2>&1; then
      push_err="$(cat "${push_err_file}")"
      git tag -d "${new_tag}" >/dev/null 2>&1 || true
      if [[ "${push_err}" == *"already exists"* ]]; then
        echo "Tag collision for ${new_tag}. Enable workflow concurrency (cancel-in-progress: false) and rerun." >&2
        echo "${push_err}" >&2
        exit 1
      fi
      echo "${push_err}" >&2
      exit 1
    fi

    if [[ "${write_major_tag}" == "true" ]]; then
      major_tag="${tag_prefix}${next_version%%.*}"
      log_info "write-major-tag=true; updating floating major tag ${major_tag}"
      git tag -f "${major_tag}" >/dev/null 2>&1 || true
      if ! git push -f origin "refs/tags/${major_tag}" >"${push_err_file}" 2>&1; then
        cat "${push_err_file}" >&2
        exit 1
      fi
    fi
  fi

  {
    echo "new-tag=${new_tag}"
    echo "previous-tag=${previous_tag}"
    echo "version-bump-used=${version_bump}"
  } >> "${GITHUB_OUTPUT}"
  log_info "Wrote outputs new-tag=${new_tag} previous-tag=${previous_tag} version-bump-used=${version_bump}"
}

log_info() {
  echo "[simple-semver] $*"
}

normalize_label() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
}

label_is_ignored() {
  local candidate="$1"
  local ignored_label normalized_ignored

  if [[ -z "${ignore_labels}" ]]; then
    return 1
  fi

  IFS=',' read -r -a ignored_labels_array <<< "${ignore_labels}"
  for ignored_label in "${ignored_labels_array[@]}"; do
    normalized_ignored="$(normalize_label "${ignored_label}")"
    if [[ -n "${normalized_ignored}" ]] && [[ "${candidate}" == "${normalized_ignored}" ]]; then
      return 0
    fi
  done

  return 1
}

resolve_bump_from_labels() {
  local pr_number="$1"
  local labels="$2"
  local label normalized_label bump
  local -a matched_bumps=()

  while IFS= read -r label; do
    normalized_label="$(normalize_label "${label}")"

    if [[ -z "${normalized_label}" ]] || label_is_ignored "${normalized_label}"; then
      continue
    fi

    case "${normalized_label}" in
      semver:major)
        bump="major"
        ;;
      semver:minor)
        bump="minor"
        ;;
      semver:patch)
        bump="patch"
        ;;
      *)
        continue
        ;;
    esac

    if [[ ! " ${matched_bumps[*]} " =~ (^|[[:space:]])${bump}($|[[:space:]]) ]]; then
      matched_bumps+=("${bump}")
    fi
  done <<< "${labels}"

  if [[ "${#matched_bumps[@]}" -gt 1 ]]; then
    echo "Multiple version labels found on PR #${pr_number}. Use only one of semver:major, semver:minor, or semver:patch." >&2
    exit 1
  fi

  if [[ "${#matched_bumps[@]}" -eq 1 ]]; then
    printf '%s\n' "${matched_bumps[0]}"
    return 0
  fi

  return 1
}

resolve_version_bump_from_pr_labels() {
  if ! validate_label_resolution_prereqs; then
    return 2
  fi

  local owner repo target_branch api_url pulls_json selected_pr_number labels
  owner="${GITHUB_REPOSITORY%%/*}"
  repo="${GITHUB_REPOSITORY#*/}"
  api_url="${GITHUB_API_URL:-https://api.github.com}"

  target_branch="${GITHUB_REF_NAME:-}"

  if ! pulls_json="$(curl \
    -fsSL \
    -H "Authorization: Bearer ${github_token}" \
    -H "Accept: application/vnd.github+json" \
    "${api_url}/repos/${owner}/${repo}/commits/${GITHUB_SHA}/pulls"
  )"; then
    echo "Failed to query pull requests for commit ${GITHUB_SHA}." >&2
    return 2
  fi

  selected_pr_number="$(printf '%s' "${pulls_json}" | jq -r --arg b "${target_branch}" '[.[] | select(.base.ref == $b)][0].number // empty')"
  if [[ -z "${selected_pr_number}" ]]; then
    return 1
  fi

  labels="$(printf '%s' "${pulls_json}" | jq -r --arg b "${target_branch}" '[.[] | select(.base.ref == $b)][0].labels[]?.name // empty')"
  resolve_bump_from_labels "${selected_pr_number}" "${labels}"
}

validate_label_resolution_prereqs() {
  if [[ -z "${github_token}" ]]; then
    echo "github-token (or GITHUB_TOKEN) is required when version-bump is empty." >&2
    return 1
  fi

  if ! command -v jq >/dev/null 2>&1; then
    echo "jq is required to resolve version bump from PR labels." >&2
    return 1
  fi

  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required to resolve version bump from PR labels." >&2
    return 1
  fi

  if [[ -z "${GITHUB_EVENT_PATH:-}" ]] || [[ ! -f "${GITHUB_EVENT_PATH}" ]]; then
    echo "GITHUB_EVENT_PATH is required to resolve version bump from PR labels." >&2
    return 1
  fi

  if [[ -z "${GITHUB_REPOSITORY:-}" ]] || [[ -z "${GITHUB_SHA:-}" ]]; then
    echo "GITHUB_REPOSITORY and GITHUB_SHA are required to resolve version bump from PR labels." >&2
    return 1
  fi

  if [[ -z "${GITHUB_REF_NAME:-}" ]]; then
    echo "GITHUB_REF_NAME is required to resolve version bump from PR labels." >&2
    return 1
  fi
}

compute_version_bump() {
  if [[ -n "${version_bump}" ]]; then
    printf '%s\n' "${version_bump}"
    return
  fi

  if resolved_bump="$(resolve_version_bump_from_pr_labels)"; then
    printf '%s\n' "${resolved_bump}"
    return
  else
    status=$?
    if [[ "${status}" -eq 2 ]]; then
      exit 1
    fi
  fi

  printf '%s\n' "patch"
}

bump_from_previous() {
  local previous_version="$1"
  local bump_type="$2"
  local major minor patch
  IFS='.' read -r major minor patch <<< "${previous_version}"
  major="${major:-0}"
  minor="${minor:-0}"
  patch="${patch:-0}"

  case "${bump_type}" in
    major)
      major=$((major + 1))
      minor=0
      patch=0
      ;;
    minor)
      minor=$((minor + 1))
      patch=0
      ;;
    patch)
      patch=$((patch + 1))
      ;;
    *)
      echo "Unsupported version bump: ${bump_type}" >&2
      exit 1
      ;;
  esac

  printf '%s\n' "${major}.${minor}.${patch}"
}

validate_latest_tag_format() {
  local latest="$1"
  if [[ ! "${latest}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Latest tag must be semantic version format ${tag_prefix}X.Y.Z, but got ${tag_prefix}${latest}. Fix tags or set an explicit version-bump." >&2
    exit 1
  fi
}

resolve_latest_semver_tag() {
  local tag semver_tags
  semver_tags=()
  while IFS= read -r tag; do
    semver_tags+=("${tag#"${tag_prefix}"}")
  done < <(git tag -l "${tag_prefix}[0-9]*.[0-9]*.[0-9]*" --sort=-version:refname)

  if [[ "${#semver_tags[@]}" -eq 0 ]]; then
    printf '%s\n' "0.0.0"
    return
  fi

  printf '%s\n' "${semver_tags[0]}"
}

main "$@"
