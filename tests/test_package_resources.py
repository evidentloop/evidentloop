"""Package-resource smoke coverage."""

from __future__ import annotations

from importlib.resources import files

from change_audit.review.core.prompt import get_default_reviewer_template
from change_audit.validation import load_audit_schema


def test_runtime_resources_are_readable_via_importlib() -> None:
    schema = load_audit_schema()
    template = files("change_audit.renderers").joinpath(
        "templates/audit.html.j2"
    ).read_text(encoding="utf-8")
    css = files("change_audit.renderers").joinpath("static/audit.css").read_text(
        encoding="utf-8"
    )
    javascript = files("change_audit.renderers").joinpath(
        "static/audit.js"
    ).read_text(encoding="utf-8")
    prompt = get_default_reviewer_template()

    assert schema["$schema"].endswith("2020-12/schema")
    assert "<!doctype html>" in template
    assert "prefers-reduced-motion" in css
    assert "changeAuditReady" in javascript
    assert "product/v0.2" in prompt
    assert "Simplified Chinese" in prompt
