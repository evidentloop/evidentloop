"""HTML renderer behavior, trace, XSS, and atomic output tests."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

import pytest

from evidentloop.audit.feedback import normalize_feedback
from evidentloop.audit.revision import audit_sha256, build_feedback_revision
from evidentloop.renderers.html import (
    AuditRenderError,
    render_audit_data,
    render_audit_file,
    validate_html_trace,
)
from tests.audit_helpers import demo_audit, minimal_audit, unanchored_finding_audit


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finding_details_tag(html: str, finding_id: str) -> str:
    match = re.search(rf'<details id="{re.escape(finding_id)}"[^>]*>', html)
    assert match is not None
    return match.group(0)


def _revised_audit() -> dict:
    source = demo_audit()
    raw = (json.dumps(source, ensure_ascii=False, indent=2) + "\n").encode()
    source_hash = audit_sha256(raw)
    events = []
    for finding in (node for node in source["nodes"] if node["type"] == "finding"):
        events.append(
            {
                "target_type": "finding",
                "target_id": finding["id"],
                "action": "false_positive",
                "fingerprint": finding["fingerprint"],
                "graph_id": source["graph_id"],
                "run_id": source["runs"][-1]["id"],
                "created_at": "2026-07-17T10:00:00+08:00",
                "source_audit_sha256": source_hash,
            }
        )
    normalized, _ = normalize_feedback(events)
    return build_feedback_revision(source, normalized, source_hash=source_hash)


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


def _semantic_summary_fixture() -> dict:
    audit = minimal_audit()
    primary = next(node for node in audit["nodes"] if node["type"] == "change")
    primary["summary"] = "本次改动把单次报告升级为可追踪的审计闭环。"
    primary["extensions"] = {
        "evidentloop": {"review_focus": "重点核验来源身份和报告可读性。"}
    }
    for index, values in enumerate(
        [
            ("统一审计契约", "结论和严重程度分别表达。", "报告契约与校验"),
            ("建立修复验证", "新 diff 可以核验旧问题。", "审计流程与模型提示"),
        ],
        start=2,
    ):
        title, summary, impact = values
        change_id = f"change-{index:03d}"
        audit["nodes"].append(
            {
                "id": change_id,
                "type": "change",
                "title": title,
                "summary": summary,
                "extensions": {"evidentloop": {"impact": impact}},
            }
        )
        audit["edges"].append(
            {
                "id": f"edge-run-change-{index}",
                "type": "contains_change",
                "from": audit["runs"][0]["id"],
                "to": change_id,
            }
        )
    return audit


def test_reference_demo_renders_full_dual_line_hunks_and_trace() -> None:
    audit = demo_audit()
    html = render_audit_data(audit)
    assert '<table class="hunk-table"' in html
    assert "<th>旧行</th><th>新行</th>" in html
    assert "变更声明判断" in html
    assert ">模型判断：不认可<" in html
    assert "模型原判断：不认可" not in html
    assert "当前裁定：相关问题已忽略" not in html
    assert "查看待处理问题（1）" in html
    assert ">partial</span>" not in html
    assert 'data-node-id="finding-001"' in html
    assert 'data-edge-id="edge-008"' in html
    assert 'data-claim-id="claim-001"' in html
    assert 'data-run-id="' in html
    assert "<dt>当前 run</dt>" not in html
    assert 'data-feedback-for="finding-001"' in html
    assert 'data-feedback-action="accept"' in html
    assert 'data-feedback-action="false_positive"' in html
    assert "data-feedback-comment" in html
    assert "data-feedback-severity" in html
    assert 'class="details-chevron"' in html
    assert ">⌄<" not in html
    assert "data-feedback-export" in html
    assert "audit-feedback.jsonl" in html
    assert "隔离宿主审查标记" in html
    assert html.index('class="panel findings-section"') < html.index(
        'class="panel feedback-export"'
    )
    assert "<pre" not in html
    assert validate_html_trace(html, audit) == []


def test_renderer_marks_synthetic_replay_provenance() -> None:
    audit = minimal_audit()
    audit["source"]["extensions"] = {
        "evidentloop": {
            "execution_mode": "demo_replay",
            "fixture_id": "synthetic-off-by-one-v1",
            "reviewer": "frozen_replay",
            "live_ai_review": False,
        }
    }

    html = render_audit_data(audit)

    assert 'data-demo-provenance="frozen-replay"' in html
    assert "synthetic-off-by-one-v1" in html
    assert "没有执行实时 AI 审查" in html


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
    assert "无待处理问题" in html
    assert "输出完整" in html
    assert 'class="status-note"' not in html
    assert "报告说明" not in html
    assert "findings-section" not in html
    assert 'class="panel feedback-export"' not in html
    assert '<div class="change-claims"' not in html
    assert '<section class="panel fix-verification-section">' not in html
    assert '<section class="panel feedback-history-section">' not in html
    assert '<section class="panel fixes-section">' not in html


@pytest.mark.parametrize(
    "status, expected",
    [
        ("not_reviewed", "未审查"),
        ("partial", "部分完成"),
        ("failed", "审查失败"),
    ],
)
def test_incomplete_states_are_never_rendered_as_clean(
    status: str, expected: str
) -> None:
    audit = minimal_audit(review_status=status, verdict="inconclusive")
    html = render_audit_data(audit)
    assert expected in html
    assert "报告说明" in html
    assert "无待处理问题" not in html


def test_semantic_change_summary_uses_dynamic_themes_and_keeps_file_details() -> None:
    audit = _semantic_summary_fixture()

    html = render_audit_data(audit)

    assert "本次改动把单次报告升级为可追踪的审计闭环" in html
    assert "统一审计契约" in html
    assert "建立修复验证" in html
    assert "影响范围：</strong>报告契约与校验" in html
    assert "重点核验来源身份和报告可读性" in html
    assert "变更规模：</strong>1 个文件，新增 1 行、删除 1 行" in html
    assert "src/example.py" in html
    assert html.count('class="change-theme"') == 2
    assert validate_html_trace(html, audit) == []


def test_unanchored_only_finding_renders_triage_without_fake_code_hunk() -> None:
    html = render_audit_data(unanchored_finding_audit())
    assert "需要人工分诊" in html
    assert "语义发现，位置未精确锚定" in html
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
    assert "d5ef26de..9a64e5a9" in html


def test_trace_validator_rejects_unknown_ids_and_remote_resources() -> None:
    audit = minimal_audit()
    html = render_audit_data(audit)
    broken = html.replace("change-minimal", "change-missing", 1).replace(
        "</head>", '<script src="https://example.invalid/x.js"></script></head>'
    )
    errors = validate_html_trace(broken, audit)
    assert any("unknown entity" in error for error in errors)
    assert any("remote" in error for error in errors)


def test_trace_validator_rejects_mismatched_audit_byte_identity() -> None:
    audit = minimal_audit()
    raw = (json.dumps(audit, ensure_ascii=False, indent=2) + "\n").encode()
    expected_hash = audit_sha256(raw)
    html = render_audit_data(audit, source_audit_sha256=expected_hash)
    broken = html.replace(expected_hash, "sha256:" + "0" * 64, 1)

    errors = validate_html_trace(
        broken,
        audit,
        source_audit_sha256=expected_hash,
    )

    assert "HTML data-audit-sha256 does not match audit.json bytes" in errors


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
    assert any(
        "missing anchored hunk: hunk:src/auth_service.py:38:1" in error
        for error in errors
    )
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
    assert f'data-audit-sha256="sha256:{input_hash}"' in output_path.read_text(
        encoding="utf-8"
    )
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
    assert "@media (max-width: 390px)" in html
    assert "@media (prefers-reduced-motion: reduce)" in html
    assert "overflow-x: hidden" not in html
    assert "max-height: 480px; overflow: auto" in html
    assert "overscroll-behavior-x: contain" in html
    assert "overscroll-behavior: contain" not in html
    assert ".hunk-table { width: max-content; min-width: 100%;" in html
    assert "white-space: pre;" in html
    assert "min-width: 42rem" not in html
    assert "min-height: 44px" in html
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in html
    assert ".finding-position {" in html
    assert ".hero-heading > div { flex: 1; }" in html
    assert "grid-template-columns: minmax(14rem, .35fr) minmax(0, 1fr);" in html
    assert ".feedback-comment-actions { display: flex; grid-column: 2;" in html
    assert ".change-claim > .claim-status { align-self: start; }" in html
    assert ".history-actions { min-width: 0; padding-left: 20px;" in html
    assert ".history-event { display: grid;" in html
    assert ".history-event-target { min-width: 0;" in html
    assert "text-wrap: wrap" in html
    assert "font-size: .9rem" in html
    assert "background-position: right 12px center" in html
    assert "appearance: none" in html
    assert ".feedback-controls select:open {" in html
    assert "repeat(auto-fit, minmax(min(100%, 28rem), 1fr))" in html
    assert ".finding-header::-webkit-details-marker { display: none; }" in html
    assert (
        ".finding-header { display: grid; grid-template-columns: minmax(0, 1fr) auto; "
        "row-gap: 8px; }"
    ) in html
    assert ".finding-summary-meta { grid-column: 1 / -1; justify-self: end; }" in html
    assert ".finding-card:not([open]) .location" not in html
    assert ".finding-card[open] .finding-toggle-closed { display: none; }" in html


def test_user_facing_renderer_labels_are_chinese() -> None:
    html = render_audit_data(demo_audit())
    assert "待处理问题" in html
    assert "当前问题与裁定" in html
    assert ">问题 1/2</span>" in html
    assert ">问题 2/2</span>" in html
    assert " open" in _finding_details_tag(html, "finding-001")
    assert " open" in _finding_details_tag(html, "finding-002")
    first_summary = html[
        html.index('<summary class="finding-header">') : html.index("</summary>")
    ]
    assert first_summary.index('class="status-chip state-open">待处理') < (
        first_summary.index('class="finding-title"')
    )
    summary_action = first_summary[first_summary.index('class="finding-summary-meta"') :]
    assert 'class="status-chip state-open"' not in summary_action
    assert "查看详情" in html
    assert "收起详情" in html
    assert "建议怎么改" in html
    assert "在 refresh 成功后立即更新缓存" in html
    assert '<section class="panel fixes-section">' not in html
    assert "来源：finding-001" not in html
    assert ">缺陷<" not in html
    assert 'data-category="bug"' in html
    assert ">更新我的裁定<" in html
    assert "可信节选" not in html  # reference fixture hunks are short and fully shown
    assert "Human decision" not in html
    assert "Open findings" not in html
    assert ">Bugs<" not in html


def test_renderer_hides_evidence_that_only_repeats_finding_title() -> None:
    audit = demo_audit()
    finding = next(node for node in audit["nodes"] if node["id"] == "finding-001")
    evidence = next(node for node in audit["nodes"] if node["id"] == "evidence-002")
    evidence["summary"] = f"宿主语义审查结论：{finding['title']}"

    html = render_audit_data(audit)
    first_card = html[
        html.index('id="finding-001"') : html.index('id="finding-002"')
    ]

    assert evidence["summary"] not in first_card
    evidence["summary"] = "宿主语义审查结论：缓存命中会绕过 refresh 路径"
    html = render_audit_data(audit)
    first_card = html[
        html.index('id="finding-001"') : html.index('id="finding-002"')
    ]
    assert evidence["summary"] in first_card


def test_feedback_revision_keeps_model_human_and_current_judgments_distinct() -> None:
    html = render_audit_data(_revised_audit())

    assert "模型原判断" in html
    assert "我的裁定" in html
    assert "0 项待处理问题" in html
    assert "报告已按人工裁定更新；未重新审查代码，模型原判断仍保留。" in html
    assert html.count('class="status-note"') == 1
    assert "误报" in html
    assert "模型原判断：不认可" in html
    assert "当前裁定：相关问题已忽略" in html
    assert html.count("查看已忽略问题（1）") == 2
    assert 'class="change-claim status-challenged related-dismissed"' in html
    assert ".change-claim.related-dismissed," in html
    assert "反馈与复审历史" in html
    assert "报告变化" in html
    assert 'class="history-actions"' in html
    assert "本轮裁定" in html
    assert 'class="history-event-target">旧 token 仍可能被缓存层返回<' in html
    assert 'class="history-event-action">标记误报<' in html
    assert "结论：存在待处理问题 → 无待处理问题" in html
    assert "严重程度：高 → 无" in html
    assert "待处理问题：2 → 0" in html
    assert "旧 token 仍可能被缓存层返回" in html
    assert "finding-001 ·" not in html
    dismissed_tag = _finding_details_tag(html, "finding-001")
    assert 'class="finding-card severity-high state-dismissed"' in dismissed_tag
    assert " open" not in dismissed_tag
    assert "原严重度：高" in html
    assert (
        ".finding-card.state-dismissed { border-left-color: var(--line-strong); }"
        in html
    )
    assert ".finding-card.state-dismissed .badge-row .status-chip" in html
    assert ".finding-card.state-dismissed .finding-fixes" in html
    assert "报告身份与校验信息" in html
    assert "交给 AI 更新报告" in html
    assert "下载 JSONL" in html


def test_feedback_revision_escapes_untrusted_human_comment() -> None:
    source = _revised_audit()
    source_hash = audit_sha256(
        (json.dumps(source, ensure_ascii=False, indent=2) + "\n").encode()
    )
    finding = next(node for node in source["nodes"] if node["type"] == "finding")
    attack = '</script><script data-human-attack="1">alert(1)</script>'
    events, _ = normalize_feedback(
        [
            {
                "target_type": "finding",
                "target_id": finding["id"],
                "action": "comment",
                "fingerprint": finding["fingerprint"],
                "graph_id": source["graph_id"],
                "run_id": source["runs"][-1]["id"],
                "created_at": "2026-07-17T10:05:00+08:00",
                "source_audit_sha256": source_hash,
                "comment": attack,
            }
        ]
    )
    revised = build_feedback_revision(source, events, source_hash=source_hash)

    html = render_audit_data(revised)

    assert attack not in html
    assert "&lt;/script&gt;" in html
    assert 'data-human-attack="1"' not in html
    assert "报告结论未变化" in html
