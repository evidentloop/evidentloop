"""Unified diff hunk parser tests."""

from __future__ import annotations

import pytest

from change_audit.renderers.hunk import HunkParseError, parse_hunk


def test_parse_hunk_tracks_old_and_new_numbers() -> None:
    parsed = parse_hunk("@@ -10,2 +10,3 @@\n same\n-old\n+new\n+extra")

    assert [(line.kind, line.old_number, line.new_number) for line in parsed.lines] == [
        ("context", 10, 10),
        ("delete", 11, None),
        ("add", None, 11),
        ("add", None, 12),
    ]
    assert parsed.line_numbers("old") == {10, 11}
    assert parsed.line_numbers("new") == {10, 11, 12}


@pytest.mark.parametrize(
    "hunk, message",
    [
        ("not a hunk", "header"),
        ("@@ -1 +1 @@\nline", "prefix"),
        ("@@ -1,2 +1,2 @@\n one", "count mismatch"),
        ("@@ -1 +1 @@\n one\n@@ -3 +3 @@", "more than one"),
    ],
)
def test_invalid_hunks_fail_with_specific_boundary(hunk: str, message: str) -> None:
    with pytest.raises(HunkParseError, match=message):
        parse_hunk(hunk)
