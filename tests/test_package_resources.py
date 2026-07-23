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
    template = (
        files("evidentloop.renderers")
        .joinpath("templates/audit.html.j2")
        .read_text(encoding="utf-8")
    )
    css = (
        files("evidentloop.renderers")
        .joinpath("static/audit.css")
        .read_text(encoding="utf-8")
    )
    javascript = (
        files("evidentloop.renderers")
        .joinpath("static/audit.js")
        .read_text(encoding="utf-8")
    )
    prompt = get_default_reviewer_template()
    demo_fixture = json.loads(
        files("evidentloop.demo_resources")
        .joinpath("fixture.json")
        .read_text(encoding="utf-8")
    )

    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["$id"] == (
        "https://evidentloop.github.io/evidentloop/schemas/audit-v0.5.schema.json"
    )
    assert schema["title"] == "EvidentLoop code-diff audit profile"
    assert schema["properties"]["schema_version"]["const"] == "0.5"
    assert not files("evidentloop.schemas").joinpath("audit-v0.4.schema.json").is_file()
    assert "<!doctype html>" in template
    assert "EvidentLoop · 代码变更" in template
    assert "prefers-reduced-motion" in css
    assert "EvidentLoopFeedback" in javascript
    assert "evidentloopReady" in javascript
    assert PRODUCT_REVIEWER_PROMPT_VERSION == "v0.7"
    assert prompt.startswith("# EvidentLoop Reviewer Prompt Template (product/v0.7)\n")
    assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == (
        "6d22df7e7cb6f7f1a7ae093edeefb478fa56d808bd57ccf710fa153b32b3f9b2"
    )
    # Freeze both resource identity and protocol wording for packaged artifacts.
    protocol_body = prompt.partition("\n")[2]
    assert hashlib.sha256(protocol_body.encode("utf-8")).hexdigest() == (
        "6bcc42aa527018228d8ca66154544ab2edc4bd58cb3455f3c40815c9ccbdb8e9"
    )
    assert "Simplified Chinese" in prompt
    assert demo_fixture["fixture_id"] == "synthetic-off-by-one-v1"
    assert "Section 1: Findings" in demo_fixture["review_response"]
