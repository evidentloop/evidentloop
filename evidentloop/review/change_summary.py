"""Parse the reviewer's optional semantic change summary."""

from __future__ import annotations

import re
from typing import Any


_SECTION_RE = re.compile(
    r"(?ms)^#+\s*Section 0:\s*Change Summary\s*(.*?)(?=^#+\s*Section 1:|\Z)"
)
_THEME_RE = re.compile(r"(?ms)^###\s+(theme-\d+)\s*(.*?)(?=^###\s+theme-\d+|\Z)")
_THEME_HEADING_RE = re.compile(r"(?m)^###\s+(.+?)\s*$")
_FIELD_RE_TEMPLATE = r"(?m)^-\s*\*\*{label}\*\*:\s*(.+?)\s*$"


def _field(block: str, label: str) -> str | None:
    matches = re.findall(_FIELD_RE_TEMPLATE.format(label=re.escape(label)), block)
    if len(matches) != 1:
        return None
    value = re.sub(r"\s+", " ", matches[0]).strip()
    return value or None


def parse_change_summary(raw_analysis: str) -> dict[str, Any] | None:
    """Return one overview and the model-selected themes, or no summary."""
    sections = list(_SECTION_RE.finditer(raw_analysis))
    if len(sections) != 1:
        return None

    body = sections[0].group(1)
    overview = _field(body, "Overview")
    review_focus = _field(body, "Review focus")
    headings = _THEME_HEADING_RE.findall(body)
    entries = _THEME_RE.findall(body)
    expected_headings = [
        f"theme-{index:03d}" for index in range(1, len(entries) + 1)
    ]
    if (
        overview is None
        or review_focus is None
        or not 1 <= len(entries) <= 5
        or len(headings) != len(entries)
        or headings != expected_headings
    ):
        return None

    themes: list[dict[str, str]] = []
    for _theme_id, block in entries:
        title = _field(block, "Title")
        summary = _field(block, "Summary")
        impact = _field(block, "Impact")
        if title is None or summary is None or impact is None:
            return None
        themes.append({"title": title, "summary": summary, "impact": impact})

    return {
        "overview": overview,
        "review_focus": review_focus,
        "themes": themes,
    }
