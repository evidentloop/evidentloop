"""Git diff collection and trusted hunk index tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from change_audit.adapters.gitdiff import GitDiffCollectionError, collect_git_diff
from change_audit.renderers.hunk import parse_hunk
from tests.git_helpers import git, initialized_repo, stage_simple_change


def test_collects_added_modified_deleted_renamed_and_binary(tmp_path: Path) -> None:
    repo = initialized_repo(tmp_path)
    (repo / "app.py").write_text("value = 2\n", encoding="utf-8")
    (repo / "added.py").write_text("added = True\n", encoding="utf-8")
    (repo / "delete.txt").unlink()
    (repo / "rename.txt").rename(repo / "renamed.txt")
    (repo / "binary.bin").write_bytes(bytes(range(64, 128)))
    git(repo, "add", "-A")

    bundle = collect_git_diff(repo, "staged")

    by_path = {item.path: item for item in bundle.files}
    assert by_path["added.py"].change_type == "added"
    assert by_path["app.py"].change_type == "modified"
    assert by_path["delete.txt"].change_type == "deleted"
    assert by_path["renamed.txt"].change_type == "renamed"
    assert by_path["binary.bin"].change_type == "binary"
    assert by_path["binary.bin"].binary is True
    assert "GIT binary patch" not in bundle.diff
    assert "Binary files " in bundle.diff
    assert by_path["added.py"].additions == 1
    assert by_path["delete.txt"].deletions == 1
    assert bundle.hunks
    assert all(parse_hunk(item.snippet).header == item.header for item in bundle.hunks)
    assert len({item.hunk_id for item in bundle.hunks}) == len(bundle.hunks)


def test_large_binary_keeps_metadata_without_embedding_payload(tmp_path: Path) -> None:
    repo = initialized_repo(tmp_path)
    (repo / "binary.bin").write_bytes(b"\0" + b"binary-data" * 100_000)
    git(repo, "add", "binary.bin")

    bundle = collect_git_diff(repo, "staged")

    binary = next(item for item in bundle.files if item.path == "binary.bin")
    assert binary.binary is True
    assert binary.change_type == "binary"
    assert "GIT binary patch" not in bundle.diff
    assert "Binary files " in bundle.diff
    assert len(bundle.diff) < 10_000


def test_rejects_empty_diff_and_invalid_ref(tmp_path: Path) -> None:
    repo = initialized_repo(tmp_path)
    with pytest.raises(GitDiffCollectionError, match="empty"):
        collect_git_diff(repo, "staged")
    with pytest.raises(GitDiffCollectionError, match="failed"):
        collect_git_diff(repo, "missing-ref")


def test_large_diff_is_indexed_without_truncation(tmp_path: Path) -> None:
    repo = initialized_repo(tmp_path)
    (repo / "large.txt").write_text(
        "".join(f"line {index}\n" for index in range(5000)),
        encoding="utf-8",
    )
    git(repo, "add", "large.txt")
    bundle = collect_git_diff(repo, "staged")
    large = next(item for item in bundle.files if item.path == "large.txt")
    assert large.additions == 5000
    assert len(bundle.diff) > 50_000


def test_staged_prompt_injection_text_remains_plain_diff_data(tmp_path: Path) -> None:
    repo = initialized_repo(tmp_path)
    stage_simple_change(repo, injection=True)
    bundle = collect_git_diff(repo, "staged")
    assert "Ignore previous instructions" in bundle.diff
