"""Package-resource smoke coverage."""

from __future__ import annotations

import hashlib
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
    assert PRODUCT_REVIEWER_PROMPT_VERSION == "v0.4"
    assert prompt.startswith("# EvidentLoop Reviewer Prompt Template (product/v0.4)\n")
    assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == (
        "e76a6d2bdbef6d67ffc62febf9457c300f28bd7c04cdf37bf7a127e7dda8ef11"
    )
    # The identity/version heading changed; the reviewer protocol body did not.
    protocol_body = prompt.partition("\n")[2]
    assert hashlib.sha256(protocol_body.encode("utf-8")).hexdigest() == (
        "d20d5af60cf26c99b4f34a96de61f6013785928c7d435ee8e849dbc220c8ebc6"
    )
    assert "Simplified Chinese" in prompt
