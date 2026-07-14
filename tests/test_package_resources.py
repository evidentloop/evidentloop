"""Package-resource smoke coverage."""

from __future__ import annotations

import hashlib
import json
from importlib.resources import files

from evidentloop.review.core.prompt import (
    PRODUCT_REVIEWER_PROMPT_VERSION,
    get_default_reviewer_template,
)
from evidentloop.validation import load_audit_schema


def test_runtime_resources_are_readable_via_importlib() -> None:
    schema = load_audit_schema()
    template = files("evidentloop.renderers").joinpath(
        "templates/audit.html.j2"
    ).read_text(encoding="utf-8")
    css = files("evidentloop.renderers").joinpath("static/audit.css").read_text(
        encoding="utf-8"
    )
    javascript = files("evidentloop.renderers").joinpath(
        "static/audit.js"
    ).read_text(encoding="utf-8")
    prompt = get_default_reviewer_template()
    demo_fixture = json.loads(
        files("evidentloop.demo_resources")
        .joinpath("fixture.json")
        .read_text(encoding="utf-8")
    )

    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["$id"] == (
        "https://evidentloop.github.io/evidentloop/schemas/audit-v0.3.schema.json"
    )
    assert schema["title"] == "EvidentLoop code-diff audit profile"
    assert schema["properties"]["schema_version"]["const"] == "0.3"
    assert "<!doctype html>" in template
    assert "EvidentLoop · 代码变更" in template
    assert "prefers-reduced-motion" in css
    assert "EvidentLoopFeedback" in javascript
    assert "evidentloopReady" in javascript
    assert PRODUCT_REVIEWER_PROMPT_VERSION == "v0.5"
    assert prompt.startswith("# EvidentLoop Reviewer Prompt Template (product/v0.5)\n")
    assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == (
        "d29412887eb5238d71e91d6a39dbb893b2435cf35d9d2e6430d1976402a2aecf"
    )
    # Freeze both resource identity and protocol wording for packaged artifacts.
    protocol_body = prompt.partition("\n")[2]
    assert hashlib.sha256(protocol_body.encode("utf-8")).hexdigest() == (
        "01ddcd3f5eb89c26d675fd68d07587e4ba4a8fc481e2de6d0d912d845583d451"
    )
    assert "Simplified Chinese" in prompt
    assert demo_fixture["fixture_id"] == "synthetic-off-by-one-v1"
    assert "Section 1: Findings" in demo_fixture["review_response"]
