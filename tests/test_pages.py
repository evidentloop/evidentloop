from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: Counter[str] = Counter()
        self.attributes: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.tags[tag] += 1
        self.attributes.append((tag, {key: value or "" for key, value in attrs}))


@pytest.mark.parametrize(
    ("relative_path", "language"),
    [("docs/index.html", "en"), ("docs/zh-CN.html", "zh-CN")],
)
def test_pages_are_static_semantic_and_use_frozen_evidence(
    relative_path: str,
    language: str,
) -> None:
    page_path = ROOT / relative_path
    text = page_path.read_text(encoding="utf-8")
    parser = _PageParser()
    parser.feed(text)

    html = next(attrs for tag, attrs in parser.attributes if tag == "html")
    hreflangs = {
        attrs["hreflang"]
        for tag, attrs in parser.attributes
        if tag == "link" and attrs.get("rel") == "alternate"
    }

    assert html["lang"] == language
    assert parser.tags["main"] == parser.tags["h1"] == parser.tags["footer"] == 1
    assert parser.tags["section"] == 3
    assert parser.tags["script"] == 0
    assert hreflangs == {"en", "zh-CN", "x-default"}

    localized_lifecycle = (
        "assets/evidentloop-lifecycle.svg"
        if language == "en"
        else "assets/evidentloop-lifecycle-zh-CN.svg"
    )
    for asset in (
        "assets/site.css",
        "assets/evidentloop-hero-sketch.jpg",
        "assets/evidentloop-report-loop.gif",
        "assets/evidentloop-report-loop.png",
        localized_lifecycle,
        "examples/evidentloop-dogfood-v05/audit.html",
        "examples/evidentloop-dogfood-v05/audit.json",
    ):
        assert (page_path.parent / asset).is_file()
        assert f"./{asset}" in text

    lowered = text.lower()
    assert "43/43" in text
    assert "schema 0.5" in lowered
    assert "schema 0.4" not in lowered
    assert "risk score" not in lowered
    assert "risk_score" not in lowered
    assert "file://" not in lowered
    assert "fonts.googleapis.com" not in lowered
