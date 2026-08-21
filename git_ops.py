from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

from errors import ActionError

if TYPE_CHECKING:
    from config import GitHubConfig


class Git:
    def list_tags(self) -> list[str]:
        self.run("fetch", "--tags", "--force", check=False, capture_output=True)
        result = self.run(
            "tag",
            "-l",
            "--sort=-version:refname",
            capture_output=True,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def get_pull_request_labels(self, github: GitHubConfig) -> tuple[int, list[str]] | None:
        pulls = self.get_associated_pull_requests(github)
        selected_pr = next((pull for pull in pulls if pull.get("base", {}).get("ref") == github.target_branch), None)
        if selected_pr is None:
            return None

        pr_number = selected_pr.get("number")
        labels = [label.get("name", "") for label in selected_pr.get("labels", [])]
        return pr_number, labels

    def get_associated_pull_requests(self, github: GitHubConfig) -> list[dict]:
        owner, repo = github.repository.split("/", 1)
        request = urllib.request.Request(
            url=f"{github.api_url}/repos/{owner}/{repo}/commits/{github.sha}/pulls",
            headers={
                "Authorization": f"Bearer {github.token}",
                "Accept": "application/vnd.github+json",
            },
        )

        try:
            with urllib.request.urlopen(request) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise ActionError(f"Failed to query pull requests for commit {github.sha}: HTTP {exc.code}.") from exc
        except urllib.error.URLError as exc:
            raise ActionError(f"Failed to query pull requests for commit {github.sha}: {exc.reason}.") from exc

    def push_tag(self, tag_name: str) -> None:
        self.delete_local_tag_if_present(tag_name)
        self.run("tag", tag_name)
        result = self.run("push", "origin", f"refs/tags/{tag_name}", check=False, capture_output=True)
        if result.returncode == 0:
            return

        self.delete_local_tag_if_present(tag_name)
        output = f"{result.stdout}{result.stderr}".strip()
        if "already exists" in output:
            raise ActionError(
                f"Tag collision for {tag_name}. Enable workflow concurrency (cancel-in-progress: false) and rerun.\n{output}"
            )

        raise ActionError(output or f"Failed to push tag {tag_name}.")

    def push_major_tag(self, tag_name: str) -> None:
        self.run("tag", "-f", tag_name, check=False, capture_output=True)
        result = self.run("push", "-f", "origin", f"refs/tags/{tag_name}", check=False, capture_output=True)
        if result.returncode != 0:
            output = f"{result.stdout}{result.stderr}".strip()
            raise ActionError(output or f"Failed to push tag {tag_name}.")

    def delete_local_tag_if_present(self, tag_name: str) -> None:
        existing = self.run("rev-parse", "-q", "--verify", f"refs/tags/{tag_name}", check=False)
        if existing.returncode == 0:
            self.run("tag", "-d", tag_name, check=False, capture_output=True)

    def run(
        self,
        *args: str,
        capture_output: bool = False,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            check=check,
            text=True,
            capture_output=capture_output,
        )
