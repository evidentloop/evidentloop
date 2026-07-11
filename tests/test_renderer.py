"""HTML renderer behavior, trace, XSS, and atomic output tests."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from change_audit.renderers.html import (
    AuditRenderError,
    render_audit_data,
    render_audit_file,
    validate_html_trace,
)
from tests.audit_helpers import demo_audit, minimal_audit, unanchored_risk_audit


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _long_hunk_audit(*, highlights: tuple[int, ...] = (50,)) -> dict:
    audit = demo_audit()
    finding = next(node for node in audit["nodes"] if node["id"] == "finding-001")
    body: list[str] = []
    for line_number in range(1, 101):
        if line_number in highlights:
            body.extend(
                [
                    f"-old value {line_number}",
                    f"+new value {line_number} <script data-line='{line_number}'>",
                ]
            )
        else:
            body.append(f" context value {line_number}")
    finding.update(
        {
            "hunk": "@@ -1,100 +1,100 @@\n" + "\n".join(body),
            "start_line": min(highlights),
            "end_line": max(highlights),
            "line_side": "new",
            "highlight_lines": list(highlights),
        }
    )
    return audit


def test_reference_demo_renders_full_dual_line_hunks_and_trace() -> None:
    audit = demo_audit()
    html = render_audit_data(audit)
    assert '<table class="hunk-table"' in html
    assert "<th>旧行</th><th>新行</th>" in html
    assert "变更目标：部分达成" in html
    assert ">partial</span>" not in html
    assert 'data-node-id="finding-001"' in html
    assert 'data-edge-id="edge-008"' in html
    assert 'data-claim-id="claim-001"' in html
    assert 'data-feedback-for="finding-001"' in html
    assert 'data-feedback-action="accept"' in html
    assert 'data-feedback-action="false_positive"' in html
    assert "data-feedback-comment" in html
    assert "data-feedback-severity" in html
    assert "data-feedback-export" in html
    assert "audit-feedback.jsonl" in html
    assert html.index('class="panel findings-section"') < html.index(
        'class="panel feedback-toolbar"'
    )
    assert "<pre" not in html
    assert validate_html_trace(html, audit) == []


def test_long_hunk_renders_bounded_trusted_excerpt_without_mutating_json() -> None:
    audit = _long_hunk_audit()
    before = copy.deepcopy(audit)

    html = render_audit_data(audit)

    assert audit == before
    assert "new value 50" in html
    assert "context value 1" not in html
    assert "context value 100" not in html
    assert "可信节选 · 展示 17/101 行" in html
    assert "省略 42 行可信 diff 内容" in html
    assert 'data-hunk-id="hunk:src/auth_service.py:38:1"' in html
    assert "<script data-line=" not in html
    assert "&lt;script data-line=&#39;50&#39;&gt;" in html
    assert validate_html_trace(html, audit) == []


def test_long_hunk_keeps_distant_highlights_with_explicit_middle_omission() -> None:
    audit = _long_hunk_audit(highlights=(20, 80))

    html = render_audit_data(audit)

    assert "new value 20" in html
    assert "new value 80" in html
    assert "context value 50" not in html
    assert "省略 44 行可信 diff 内容" in html
    assert "可信节选 · 展示 34/102 行" in html


def test_complete_clean_review_omits_empty_finding_sections() -> None:
    html = render_audit_data(minimal_audit())
    assert "候选通过" in html
    assert "审查输出已完整接收" in html
    assert "findings-section" not in html
    assert 'class="panel feedback-toolbar"' not in html
    assert "claim claim-empty" in html


@pytest.mark.parametrize(
    "status, expected",
    [
        ("not_reviewed", "审查尚未执行"),
        ("partial", "审查仅部分完成"),
        ("failed", "审查失败"),
    ],
)
def test_incomplete_states_are_never_rendered_as_clean(status: str, expected: str) -> None:
    audit = minimal_audit(review_status=status, verdict="inconclusive", risk_score=None)
    html = render_audit_data(audit)
    assert expected in html
    assert "候选通过" not in html
    assert "无法可靠评分" in html


def test_unanchored_only_risk_renders_triage_without_fake_code_hunk() -> None:
    html = render_audit_data(unanchored_risk_audit())
    assert "需要人工分诊" in html
    assert "语义发现，位置未精确锚定且未计分" in html
    assert "无法可靠评分" in html
    assert '<table class="hunk-table"' not in html


def test_jinja_autoescape_blocks_business_text_xss() -> None:
    audit = minimal_audit()
    attack = '</script><script data-attack="1">alert(1)</script>'
    audit["runs"][0]["label"] = attack
    audit["runs"][0]["summary"] = attack
    html = render_audit_data(audit)
    assert attack not in html
    assert "&lt;/script&gt;" in html
    assert 'data-attack="1"' not in html


def test_long_commit_range_is_shortened_only_in_html() -> None:
    audit = minimal_audit()
    exact_ref = (
        "d5ef26deac6b1ed37ee9b89b52dddb1bcaac6c24"
        ".."
        "9a64e5a926d430a421a71b5cf433b0553876db28"
    )
    audit["source"]["ref"] = exact_ref

    html = render_audit_data(audit)

    assert audit["source"]["ref"] == exact_ref
    assert exact_ref not in html
    assert "来源：d5ef26de..9a64e5a9" in html


def test_trace_validator_rejects_unknown_ids_and_remote_resources() -> None:
    audit = minimal_audit()
    html = render_audit_data(audit)
    broken = html.replace("change-minimal", "change-missing", 1).replace(
        "</head>", '<script src="https://example.invalid/x.js"></script></head>'
    )
    errors = validate_html_trace(broken, audit)
    assert any("unknown entity" in error for error in errors)
    assert any("remote" in error for error in errors)


def test_trace_validator_requires_all_findings_claims_hunks_and_feedback() -> None:
    audit = demo_audit()
    html = render_audit_data(audit)
    fingerprint = next(
        node["fingerprint"] for node in audit["nodes"] if node["id"] == "finding-001"
    )
    broken = (
        html.replace(f'data-fingerprint="{fingerprint}"', "", 1)
        .replace('data-claim-id="claim-001"', "", 1)
        .replace('data-hunk-id="hunk:src/auth_service.py:38:1"', "", 1)
        .replace('data-feedback-for="finding-002"', "", 1)
    )

    errors = validate_html_trace(broken, audit)

    assert any("missing finding fingerprint: finding-001" in error for error in errors)
    assert any("missing claim: claim-001" in error for error in errors)
    assert any("missing anchored hunk: hunk:src/auth_service.py:38:1" in error for error in errors)
    assert any("missing feedback target: finding-002" in error for error in errors)


def test_render_file_atomically_replaces_only_html(tmp_path: Path) -> None:
    input_path = tmp_path / "audit.json"
    output_path = tmp_path / "audit.html"
    input_path.write_text(json.dumps(minimal_audit()), encoding="utf-8")
    output_path.write_text("OLD", encoding="utf-8")
    input_hash = _sha256(input_path)

    result = render_audit_file(input_path, output_path)

    assert result == output_path
    assert output_path.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert _sha256(input_path) == input_hash
    assert list(tmp_path.glob(".audit.html.*.tmp")) == []


def test_render_failure_preserves_old_html_and_input(tmp_path: Path) -> None:
    input_path = tmp_path / "audit.json"
    output_path = tmp_path / "audit.html"
    invalid = minimal_audit()
    invalid["summary"]["finding_count"] = 9
    input_path.write_text(json.dumps(invalid), encoding="utf-8")
    output_path.write_text("OLD", encoding="utf-8")
    input_hash = _sha256(input_path)

    with pytest.raises(AuditRenderError):
        render_audit_file(input_path, output_path)

    assert output_path.read_text(encoding="utf-8") == "OLD"
    assert _sha256(input_path) == input_hash


def test_render_rejects_output_equal_to_input(tmp_path: Path) -> None:
    input_path = tmp_path / "audit.json"
    input_path.write_text(json.dumps(minimal_audit()), encoding="utf-8")
    before = input_path.read_text(encoding="utf-8")
    with pytest.raises(AuditRenderError, match="must not replace"):
        render_audit_file(input_path, input_path)
    assert input_path.read_text(encoding="utf-8") == before


def test_packaged_css_has_responsive_and_reduced_motion_guards() -> None:
    html = render_audit_data(minimal_audit())
    assert "@media (max-width: 780px)" in html
    assert "@media (prefers-reduced-motion: reduce)" in html
    assert "overflow-x: hidden" in html
    assert "overflow-x: auto" in html
    assert ".hero-copy { min-width: 0; overflow-wrap: anywhere; }" in html
    assert ".summary-grid p," in html
    assert ".section-title { align-items: flex-start; }" in html
    assert ".summary-grid { display: grid; grid-template-columns: 1.2fr .8fr; align-items: start;" in html
    assert ".hunk-table { width: 100%; min-width: 0;" in html
    assert "table-layout: fixed" in html
    assert "white-space: pre-wrap" in html
    assert "@media (max-width: 330px)" in html
    assert "min-width: 680px" not in html


def test_user_facing_renderer_labels_are_chinese() -> None:
    html = render_audit_data(demo_audit())
    assert "待处理问题" in html
    assert ">缺陷<" in html
    assert ">人工决策<" in html
    assert "可信节选" not in html  # reference fixture hunks are short and fully shown
    assert "Human decision" not in html
    assert "Open findings" not in html
    assert ">Bugs<" not in html
