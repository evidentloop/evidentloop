"""Offline synthetic replay demo for the packaged EvidentLoop workflow."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from importlib.resources import files
from pathlib import Path
from typing import Any

from .audit.finalize import _prepare_local_diff, finalize_review


class DemoError(RuntimeError):
    """Raised when the deterministic demo cannot be prepared or replayed."""


def _git(repo: Path, *args: str) -> None:
    git = shutil.which("git")
    if not git:
        raise DemoError("Git is required to run the demo")
    try:
        subprocess.run(
            [git, *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise DemoError(f"local Git fixture setup failed: {exc}") from exc


def _load_fixture() -> dict[str, Any]:
    try:
        value = json.loads(
            files("evidentloop.demo_resources")
            .joinpath("fixture.json")
            .read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DemoError(f"cannot read bundled demo fixture: {exc}") from exc
    required = {"fixture_id", "baseline", "changed", "review_response"}
    if not isinstance(value, dict) or not required.issubset(value):
        raise DemoError("bundled demo fixture is incomplete")
    return value


def run_demo(output_dir: str | Path | None = None) -> dict[str, Any]:
    """Run prepare -> frozen replay -> finalize without network or a live model."""
    fixture = _load_fixture()
    final_dir = Path(output_dir or "evidentloop-demo")
    if not final_dir.is_absolute():
        final_dir = (Path.cwd() / final_dir).resolve()

    with tempfile.TemporaryDirectory(prefix="evidentloop-demo-") as temp_root:
        repo = Path(temp_root) / "synthetic-repo"
        repo.mkdir()
        _git(repo, "init", "-q")
        _git(repo, "config", "user.email", "demo@evidentloop.invalid")
        _git(repo, "config", "user.name", "EvidentLoop Demo")
        empty_hooks = repo / ".git" / "evidentloop-empty-hooks"
        empty_hooks.mkdir()
        app = repo / "app.py"
        app.write_text(str(fixture["baseline"]), encoding="utf-8")
        _git(repo, "add", "app.py")
        _git(
            repo,
            "-c",
            f"core.hooksPath={empty_hooks}",
            "commit",
            "--no-gpg-sign",
            "-q",
            "-m",
            "synthetic baseline",
        )
        app.write_text(str(fixture["changed"]), encoding="utf-8")
        _git(repo, "add", "app.py")

        locator = _prepare_local_diff(
            repo,
            "staged",
            final_dir,
            source_extensions={
                "evidentloop": {
                    "execution_mode": "demo_replay",
                    "fixture_id": fixture["fixture_id"],
                    "reviewer": "frozen_replay",
                    "live_ai_review": False,
                }
            },
        )
        raw_analysis = (
            f"<!-- evidentloop-run-id: {locator['run_id']} -->\n"
            f"{str(fixture['review_response']).strip()}\n"
        )
        Path(locator["raw_analysis_path"]).write_text(raw_analysis, encoding="utf-8")
        result = finalize_review(locator["final_dir"])

    return {
        **result,
        "execution_mode": "demo_replay",
        "fixture_id": fixture["fixture_id"],
        "live_ai_review": False,
    }
