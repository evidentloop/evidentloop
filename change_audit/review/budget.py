"""Budget gate for ``crossreview verify``.

Applies file-count and char-count soft limits before reviewer invocation.
The first prioritized file is always included unless it breaches an absolute
hard cap, which results in ``rejected``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .pack import assemble_pack
from .schema import BudgetStatus, FileMeta, ReviewPack, ReviewerFailureReason


ABSOLUTE_MAX_FIRST_FILE_CHARS = 200_000

_DIFF_GIT_RE = re.compile(r"diff --git a/(.*?) b/(.*?)\n")


@dataclass
class BudgetGateResult:
    """Result of budget evaluation."""

    status: BudgetStatus
    effective_pack: ReviewPack | None
    files_reviewed: int
    files_total: int
    chars_consumed: int
    chars_limit: int | None
    failure_reason: ReviewerFailureReason | None = None


def _split_diff_chunks(diff: str) -> list[tuple[str, str]]:
    """Split a unified diff into (b_path, chunk) pairs keyed by destination path.

    Known v0 limitation: the ``diff --git`` header regex cannot parse git's
    C-style quoted headers or paths containing literal `` b/``
    (space-b-slash).  This mirrors the documented limitation in
    ``pack.extract_changed_files``.  Packs produced by ``crossreview pack``
    are not affected because ``changed_files_from_git`` uses NUL-delimited
    output for reliable path extraction.
    """
    if not diff.strip():
        return []

    lines = diff.splitlines(keepends=True)
    chunks: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if line.startswith("diff --git ") and current:
            chunks.append(current)
            current = [line]
            continue
        current.append(line)

    if current:
        chunks.append(current)

    result: list[tuple[str, str]] = []
    for chunk_lines in chunks:
        header = chunk_lines[0]
        if not header.startswith("diff --git "):
            return []
        m = _DIFF_GIT_RE.match(header)
        b_path = m.group(2) if m else ""
        result.append((b_path, "".join(chunk_lines)))
    return result


def _matches_focus(path: str, focus: list[str] | None) -> bool:
    if not focus:
        return False
    path_lower = path.lower()
    return any(term.lower() in path_lower for term in focus if term)


def apply_budget_gate(pack: ReviewPack) -> BudgetGateResult:
    """Apply pack budget rules and return the effective reviewer input."""
    diff_pairs = _split_diff_chunks(pack.diff)
    files_total = len(pack.changed_files)

    if not pack.changed_files or not diff_pairs:
        return BudgetGateResult(
            status=BudgetStatus.REJECTED,
            effective_pack=None,
            files_reviewed=0,
            files_total=files_total,
            chars_consumed=0,
            chars_limit=pack.budget.max_chars_total,
            failure_reason=ReviewerFailureReason.INPUT_INVALID,
        )

    # Build a path→chunk lookup from the diff so ordering doesn't matter.
    chunk_by_path: dict[str, str] = {path: chunk for path, chunk in diff_pairs}

    entries: list[tuple[FileMeta, str]] = []
    for meta in pack.changed_files:
        chunk = chunk_by_path.get(meta.path, "")
        entries.append((meta, chunk))

    # Reject if any changed file cannot be mapped back to a diff chunk.
    if any(not chunk for _, chunk in entries):
        return BudgetGateResult(
            status=BudgetStatus.REJECTED,
            effective_pack=None,
            files_reviewed=0,
            files_total=files_total,
            chars_consumed=0,
            chars_limit=pack.budget.max_chars_total,
            failure_reason=ReviewerFailureReason.INPUT_INVALID,
        )

    prioritized = [
        entry for entry in entries if _matches_focus(entry[0].path, pack.focus)
    ]
    prioritized.extend(
        entry for entry in entries if not _matches_focus(entry[0].path, pack.focus)
    )

    first_meta, first_chunk = prioritized[0]
    first_len = len(first_chunk)
    if first_len > ABSOLUTE_MAX_FIRST_FILE_CHARS:
        return BudgetGateResult(
            status=BudgetStatus.REJECTED,
            effective_pack=None,
            files_reviewed=0,
            files_total=files_total,
            chars_consumed=0,
            chars_limit=pack.budget.max_chars_total,
            failure_reason=ReviewerFailureReason.CONTEXT_TOO_LARGE,
        )

    selected_meta = [first_meta]
    selected_chunks = [first_chunk]
    chars_consumed = first_len

    max_files = pack.budget.max_files
    max_chars_total = pack.budget.max_chars_total
    truncated = (
        (max_files is not None and 1 > max_files)
        or (max_chars_total is not None and chars_consumed > max_chars_total)
    )

    for meta, chunk in prioritized[1:]:
        if max_files is not None and len(selected_meta) >= max_files:
            truncated = True
            break

        next_chars = chars_consumed + len(chunk)
        if max_chars_total is not None and next_chars > max_chars_total:
            truncated = True
            break

        selected_meta.append(meta)
        selected_chunks.append(chunk)
        chars_consumed = next_chars

    if len(selected_meta) < files_total:
        truncated = True

    effective_pack = assemble_pack(
        "".join(selected_chunks),
        changed_files=list(selected_meta),
        intent=pack.intent,
        task_file=pack.task_file,
        focus=pack.focus,
        context_files=pack.context_files,
        evidence=pack.evidence,
        budget=pack.budget,
    )

    return BudgetGateResult(
        status=BudgetStatus.TRUNCATED if truncated else BudgetStatus.COMPLETE,
        effective_pack=effective_pack,
        files_reviewed=len(selected_meta),
        files_total=files_total,
        chars_consumed=chars_consumed,
        chars_limit=max_chars_total,
    )
