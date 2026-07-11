"""Deterministic Git diff collection and trusted hunk indexing."""

from __future__ import annotations

import hashlib
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from change_audit.renderers.hunk import HunkParseError, parse_hunk
from change_audit.review.pack import build_diff_source
from change_audit.review.schema import FileMeta, GitDiffSource, to_serializable


class GitDiffCollectionError(RuntimeError):
    """Raised when a diff cannot be collected or indexed safely."""


@dataclass(frozen=True)
class DiffFile:
    """One changed file with normalized change metadata."""

    path: str
    old_path: str | None
    new_path: str | None
    change_type: str
    additions: int
    deletions: int
    binary: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HunkIndexEntry:
    """A trusted, render-ready hunk extracted from Git output."""

    hunk_id: str
    file_path: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str
    snippet: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GitDiffBundle:
    """Collected Git diff plus file metadata and trusted hunk index."""

    diff_spec: str
    diff: str
    files: tuple[DiffFile, ...]
    hunks: tuple[HunkIndexEntry, ...]
    diff_source: GitDiffSource

    @property
    def changed_files(self) -> list[FileMeta]:
        return [FileMeta(path=item.path) for item in self.files]

    def hunk_index_dict(self, *, run_id: str, artifact_fingerprint: str) -> dict[str, Any]:
        return {
            "schema_version": "1",
            "run_id": run_id,
            "artifact_fingerprint": artifact_fingerprint,
            "diff_spec": self.diff_spec,
            "diff_source": to_serializable(self.diff_source),
            "files": [item.to_dict() for item in self.files],
            "hunks": [item.to_dict() for item in self.hunks],
        }


def _diff_args(diff_spec: str) -> list[str]:
    spec = diff_spec.strip()
    if not spec:
        raise GitDiffCollectionError("diff spec must not be empty")
    if spec in {"staged", "--cached"}:
        return ["--cached"]
    if spec == "unstaged":
        return []
    if ".." in spec:
        return [spec]
    return [spec, "HEAD"]


def _run_git(repo_root: Path, args: list[str], *, binary: bool = False) -> str | bytes:
    command = ["git", "--no-pager", *args]
    try:
        result = subprocess.run(
            command,
            cwd=repo_root,
            capture_output=True,
            check=True,
            text=not binary,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        if isinstance(exc, subprocess.CalledProcessError):
            stderr = exc.stderr
            if isinstance(stderr, bytes):
                detail = stderr.decode("utf-8", errors="replace").strip()
            else:
                detail = (stderr or "").strip()
            message = f"git {' '.join(args)} failed (exit {exc.returncode}): {detail}"
        else:
            message = f"cannot execute git: {exc}"
        raise GitDiffCollectionError(message) from exc
    return result.stdout


def _parse_name_status(raw: bytes) -> list[tuple[str, str | None, str | None]]:
    tokens = raw.decode("utf-8", errors="surrogateescape").split("\0")
    if tokens and tokens[-1] == "":
        tokens.pop()
    records: list[tuple[str, str | None, str | None]] = []
    index = 0
    while index < len(tokens):
        status = tokens[index]
        index += 1
        if not status:
            raise GitDiffCollectionError("git name-status output contains an empty status")
        kind = status[0]
        if kind in {"R", "C"}:
            if index + 1 >= len(tokens):
                raise GitDiffCollectionError("git rename record is truncated")
            old_path, new_path = tokens[index], tokens[index + 1]
            index += 2
        else:
            if index >= len(tokens):
                raise GitDiffCollectionError("git name-status record is truncated")
            path = tokens[index]
            index += 1
            old_path = path if kind == "D" else None
            new_path = None if kind == "D" else path
        records.append((kind, old_path, new_path))
    return records


def _split_file_patches(diff: str) -> list[str]:
    lines = diff.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line.startswith("diff --git ")]
    patches: list[str] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        patches.append("".join(lines[start:end]))
    return patches


def _extract_hunk_snippets(patch: str) -> list[str]:
    lines = patch.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line.startswith("@@ ")]
    snippets: list[str] = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        while end > start and lines[end - 1].startswith(("diff --git ", "index ")):
            end -= 1
        snippets.append("".join(lines[start:end]).rstrip("\n"))
    return snippets


def _change_type(kind: str, *, binary: bool) -> str:
    if binary:
        return "binary"
    return {
        "A": "added",
        "D": "deleted",
        "R": "renamed",
    }.get(kind, "modified")


def collect_git_diff(repo_path: str | Path, diff_spec: str) -> GitDiffBundle:
    """Collect one non-empty Git diff and build its trusted hunk index."""
    repo_root = Path(repo_path).resolve()
    if not repo_root.is_dir():
        raise GitDiffCollectionError(f"repository path is not a directory: {repo_root}")

    args = _diff_args(diff_spec)
    diff = _run_git(repo_root, ["diff", "--find-renames", *args])
    assert isinstance(diff, str)
    if not diff.strip():
        raise GitDiffCollectionError(f"git diff is empty for spec {diff_spec!r}")

    raw_status = _run_git(
        repo_root,
        ["diff", "--find-renames", "--name-status", "-z", *args],
        binary=True,
    )
    assert isinstance(raw_status, bytes)
    statuses = _parse_name_status(raw_status)
    patches = _split_file_patches(diff)
    if len(statuses) != len(patches):
        raise GitDiffCollectionError(
            "git diff file metadata does not match unified diff sections "
            f"({len(statuses)} metadata records, {len(patches)} patches)"
        )

    files: list[DiffFile] = []
    hunks: list[HunkIndexEntry] = []
    for file_index, ((kind, old_path, new_path), patch) in enumerate(
        zip(statuses, patches, strict=True),
        start=1,
    ):
        path = new_path or old_path
        if not path:
            raise GitDiffCollectionError("changed file record has no usable path")
        binary_patch = "GIT binary patch" in patch or "Binary files " in patch
        additions = 0
        deletions = 0
        for hunk_index, snippet in enumerate(_extract_hunk_snippets(patch), start=1):
            try:
                parsed = parse_hunk(snippet)
            except HunkParseError as exc:
                raise GitDiffCollectionError(
                    f"cannot index hunk {hunk_index} for {path}: {exc}"
                ) from exc
            additions += sum(1 for line in parsed.lines if line.kind == "add")
            deletions += sum(1 for line in parsed.lines if line.kind == "delete")
            path_digest = hashlib.sha256(path.encode("utf-8", errors="surrogateescape")).hexdigest()[:16]
            anchor_start = parsed.new_start if parsed.new_count else parsed.old_start
            hunks.append(
                HunkIndexEntry(
                    hunk_id=f"hunk:{path_digest}:{anchor_start}:{hunk_index}",
                    file_path=path,
                    old_start=parsed.old_start,
                    old_count=parsed.old_count,
                    new_start=parsed.new_start,
                    new_count=parsed.new_count,
                    header=parsed.header,
                    snippet=snippet,
                )
            )
        files.append(
            DiffFile(
                path=path,
                old_path=old_path,
                new_path=new_path,
                change_type=_change_type(kind, binary=binary_patch),
                additions=additions,
                deletions=deletions,
                binary=binary_patch,
            )
        )

    staged = diff_spec.strip() in {"staged", "--cached"}
    source_ref = None if diff_spec.strip() == "unstaged" else diff_spec.strip()
    source = build_diff_source(source_ref, staged)
    return GitDiffBundle(
        diff_spec=diff_spec,
        diff=diff,
        files=tuple(files),
        hunks=tuple(hunks),
        diff_source=source,
    )
