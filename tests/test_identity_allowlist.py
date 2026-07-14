"""Prevent the retired product identity from returning to active surfaces."""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OLD_HYPHEN = "change" + "-audit"
OLD_UNDERSCORE = "change" + "_audit"
OLD_MARKERS = (OLD_HYPHEN, OLD_UNDERSCORE)
ALLOWED_PREFIXES = (
    ".sopify/history/",
    ".sopify/plan/20260711_identity_and_distribution/",
    "docs/examples/",
)
ALLOWED_VISUALS = {
    f"docs/assets/{OLD_HYPHEN}-architecture.svg",
    f"docs/assets/{OLD_HYPHEN}-architecture.png",
    f"docs/assets/{OLD_HYPHEN}-review-flow.svg",
    f"docs/assets/{OLD_HYPHEN}-review-flow.png",
}
ALLOWED_REMOTE_URLS = (
    f"https://github.com/evidentloop/{OLD_HYPHEN}.git",
    f"git@github.com:evidentloop/{OLD_HYPHEN}.git",
)


def _allowed_path(relative_path: str) -> bool:
    return relative_path.startswith(ALLOWED_PREFIXES) or relative_path in ALLOWED_VISUALS


def test_retired_identity_is_confined_to_the_explicit_allowlist() -> None:
    tracked_and_pending = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    violations: list[str] = []

    for relative_path in sorted(set(tracked_and_pending)):
        if _allowed_path(relative_path):
            continue
        lowered_path = relative_path.lower()
        if any(marker in lowered_path for marker in OLD_MARKERS):
            violations.append(f"{relative_path}: legacy identity in path")
            continue
        try:
            text = (ROOT / relative_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for remote_url in ALLOWED_REMOTE_URLS:
            text = text.replace(remote_url, "")
        for line_number, line in enumerate(text.splitlines(), start=1):
            lowered_line = line.lower()
            if any(marker in lowered_line for marker in OLD_MARKERS):
                violations.append(f"{relative_path}:{line_number}")

    assert not violations, "retired identity escaped allowlist:\n" + "\n".join(
        violations
    )
