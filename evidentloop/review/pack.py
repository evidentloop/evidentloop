"""Construct and serialize ReviewPack values from trusted adapter inputs.

Design decisions:
  - Git collection belongs to ``evidentloop.adapters.gitdiff``.
  - ``extract_changed_files()`` is a fallback for callers that only have diff text.
  - Language detected from file extension (simple mapping).
  - Fingerprints: artifact_fp = sha256(diff), pack_fp = sha256(pack-sans-fp).
  - pack_completeness computed per v0-scope.md §10.2 (returned, not stored on pack).
  - validate_review_pack() called before emission; violations → ValueError.
"""

from __future__ import annotations

import datetime
import json
import re
from pathlib import Path

from .schema import (
    ArtifactType,
    ContextFile,
    DiffSource,
    GitDiffSource,
    Evidence,
    FileMeta,
    PackBudget,
    ReviewPack,
    compute_fingerprint,
    to_serializable,
    validate_review_pack,
    SCHEMA_VERSION,
)


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

_LANG_MAP: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".rb": "ruby",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
    ".sql": "sql",
    ".r": "r",
    ".R": "r",
    ".lua": "lua",
    ".php": "php",
    ".pl": "perl",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hs": "haskell",
    ".scala": "scala",
    ".dart": "dart",
    ".vue": "vue",
    ".svelte": "svelte",
}


def detect_language(path: str) -> str | None:
    """Detect programming language from file extension."""
    suffix = Path(path).suffix
    return _LANG_MAP.get(suffix) or _LANG_MAP.get(suffix.lower())


def build_diff_source(ref: str | None, staged: bool) -> GitDiffSource:
    """Build a :class:`GitDiffSource` from diff collection parameters.

    Used by the Git adapter to attach provenance metadata to every ReviewPack.
    For artifact-based reviews (v1), construct :class:`ArtifactDiffSource` directly.
    """
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if staged:
        return GitDiffSource(type="staged", captured_at=now)
    if ref is None:
        return GitDiffSource(type="unstaged", captured_at=now)
    if ".." in ref:
        # Detect three-dot ("main...feat") vs two-dot ("main..feat") range syntax before
        # splitting, so head doesn't get a spurious leading dot.
        sep = "..." if "..." in ref else ".."
        parts = ref.split(sep, 1)
        return GitDiffSource(type="range", base=parts[0], head=parts[1])
    return GitDiffSource(type="committed", base=ref, head="HEAD")


# Regex fallback for callers with only diff text. Known limitation: fails on quoted
# paths and paths containing " b/"; the product Git adapter supplies FileMeta directly.
_DIFF_HEADER_RE = re.compile(r"^diff --git a/(.*?) b/(.*)$", re.MULTILINE)


def extract_changed_files(diff: str) -> list[FileMeta]:
    """Parse a unified diff to extract the list of changed files.

    This is a **regex fallback**. Known limitations:

    - Paths with special characters (tabs, quotes) are quoted by git and
      won't match the regex.
    - Paths containing the literal substring `` b/`` will be mis-split.

    Handles normal changes, additions, deletions, and renames.
    Deduplicates by path.
    """
    seen: dict[str, FileMeta] = {}
    for m in _DIFF_HEADER_RE.finditer(diff):
        old_path, new_path = m.group(1), m.group(2)
        # Deletions: +++ /dev/null → use old path
        path = new_path if new_path != "/dev/null" else old_path
        if path not in seen:
            seen[path] = FileMeta(path=path, language=detect_language(path))
    return list(seen.values())


# ---------------------------------------------------------------------------
# Pack completeness — v0-scope.md §10.2
# ---------------------------------------------------------------------------

def compute_pack_completeness(pack: ReviewPack) -> float:
    """Calculate pack completeness score per v0-scope.md §10.2.

    Returns a float in [0, 1]. Breakdown::

        diff non-empty          → +0.30
        changed_files populated → +0.10
        intent or task_file     → +0.25
        focus                   → +0.10
        context_files           → +0.15
        evidence                → +0.10
        ────────────────────────────────
        max                       1.00
    """
    score = 0.0
    if pack.diff:
        score += 0.30
    if pack.changed_files:
        score += 0.10
    if pack.intent or pack.task_file:
        score += 0.25
    if pack.focus:
        score += 0.10
    if pack.context_files:
        score += 0.15
    if pack.evidence:
        score += 0.10
    return round(score, 2)


# ---------------------------------------------------------------------------
# Serialization — ReviewPack → dict / JSON
# ---------------------------------------------------------------------------


def pack_to_dict(pack: ReviewPack) -> dict:
    """Convert a ReviewPack to a JSON-serializable dict."""
    return to_serializable(pack)


def pack_to_json(pack: ReviewPack, *, indent: int = 2, exclude_pack_fp: bool = False) -> str:
    """Serialize a ReviewPack to a JSON string.

    If *exclude_pack_fp* is True, ``pack_fingerprint`` is set to ``""`` in
    the output — used when computing the fingerprint itself.
    """
    d = pack_to_dict(pack)
    if exclude_pack_fp:
        d["pack_fingerprint"] = ""
    return json.dumps(d, indent=indent, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def assemble_pack(
    diff: str,
    *,
    changed_files: list[FileMeta] | None = None,
    intent: str | None = None,
    task_file: str | None = None,
    focus: list[str] | None = None,
    context_files: list[ContextFile] | None = None,
    evidence: list[Evidence] | None = None,
    budget: PackBudget | None = None,
    diff_source: DiffSource | None = None,
) -> ReviewPack:
    """Construct a validated ReviewPack from components.

    * If *changed_files* is ``None``, they are extracted from *diff*.
    * Fingerprints are computed automatically.
    * ``validate_review_pack()`` is called; violations raise ``ValueError``.
    * *diff_source* attaches provenance metadata (see :class:`DiffSource`);
      use :func:`build_diff_source` to construct it from CLI args.
    """
    if changed_files is None:
        changed_files = extract_changed_files(diff)

    artifact_fp = compute_fingerprint(diff)

    pack = ReviewPack(
        schema_version=SCHEMA_VERSION,
        artifact_type=ArtifactType.CODE_DIFF,
        diff=diff,
        changed_files=changed_files,
        artifact_fingerprint=artifact_fp,
        intent=intent,
        task_file=task_file,
        focus=focus,
        context_files=context_files,
        evidence=evidence,
        budget=budget or PackBudget(),
        diff_source=diff_source,
    )

    # pack_fingerprint = hash of pack content with pack_fp excluded
    pack.pack_fingerprint = compute_fingerprint(
        pack_to_json(pack, exclude_pack_fp=True)
    )

    violations = validate_review_pack(pack)
    if violations:
        raise ValueError(f"Invalid ReviewPack: {', '.join(violations)}")

    return pack
