from __future__ import annotations

import subprocess

from github_labels import ActionError


class Git:
    def fetch_tags(self) -> None:
        self.run("fetch", "--tags", "--force", check=False, capture_output=True)

    def list_tags(self, pattern: str) -> list[str]:
        result = self.run(
            "tag",
            "-l",
            pattern,
            "--sort=-version:refname",
            capture_output=True,
        )
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

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
