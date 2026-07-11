"""Unified-diff hunk parsing for trusted renderer input."""

from __future__ import annotations

import re
from dataclasses import dataclass


_HUNK_HEADER = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@(?P<context>.*)$"
)


class HunkParseError(ValueError):
    """Raised when a finding hunk is not a complete unified-diff hunk."""


@dataclass(frozen=True)
class HunkLine:
    """One renderable line with independent old/new coordinates."""

    kind: str
    prefix: str
    content: str
    old_number: int | None
    new_number: int | None


@dataclass(frozen=True)
class ParsedHunk:
    """Parsed header and complete line sequence."""

    header: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    context: str
    lines: tuple[HunkLine, ...]

    def line_numbers(self, side: str) -> set[int]:
        if side == "old":
            return {line.old_number for line in self.lines if line.old_number is not None}
        if side == "new":
            return {line.new_number for line in self.lines if line.new_number is not None}
        raise ValueError("side must be old or new")


def parse_hunk(value: str) -> ParsedHunk:
    """Parse one complete unified-diff hunk and verify header counts."""
    raw_lines = value.splitlines()
    if not raw_lines:
        raise HunkParseError("hunk is empty")

    match = _HUNK_HEADER.fullmatch(raw_lines[0])
    if not match:
        raise HunkParseError("invalid unified-diff hunk header")

    old_start = int(match.group("old_start"))
    old_count = int(match.group("old_count") or "1")
    new_start = int(match.group("new_start"))
    new_count = int(match.group("new_count") or "1")
    old_line = old_start
    new_line = new_start
    old_seen = 0
    new_seen = 0
    parsed: list[HunkLine] = []

    for index, line in enumerate(raw_lines[1:], start=2):
        if line.startswith("@@"):
            raise HunkParseError("finding hunk contains more than one header")
        if line.startswith("\\ No newline at end of file"):
            parsed.append(HunkLine("meta", "\\", line[1:], None, None))
            continue
        if not line:
            raise HunkParseError(f"line {index} has no unified-diff prefix")

        prefix = line[0]
        content = line[1:]
        if prefix == " ":
            parsed.append(HunkLine("context", prefix, content, old_line, new_line))
            old_line += 1
            new_line += 1
            old_seen += 1
            new_seen += 1
        elif prefix == "-":
            parsed.append(HunkLine("delete", prefix, content, old_line, None))
            old_line += 1
            old_seen += 1
        elif prefix == "+":
            parsed.append(HunkLine("add", prefix, content, None, new_line))
            new_line += 1
            new_seen += 1
        else:
            raise HunkParseError(f"line {index} has invalid prefix {prefix!r}")

    if old_seen != old_count or new_seen != new_count:
        raise HunkParseError(
            "hunk body count mismatch: "
            f"header old/new={old_count}/{new_count}, body={old_seen}/{new_seen}"
        )

    return ParsedHunk(
        header=raw_lines[0],
        old_start=old_start,
        old_count=old_count,
        new_start=new_start,
        new_count=new_count,
        context=match.group("context").strip(),
        lines=tuple(parsed),
    )
