"""Self-contained HTML renderer for validated code-diff audits."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict
from html.parser import HTMLParser
from importlib.resources import files
from pathlib import Path
from typing import Any, Mapping

from jinja2 import Environment, StrictUndefined, TemplateError

from ..validation import AuditValidationError, assert_valid_audit
from .hunk import ParsedHunk, parse_hunk


RENDERER_VERSION = "0.3"
FULL_HUNK_LINE_LIMIT = 40
HUNK_EXCERPT_CONTEXT_LINES = 8


class AuditRenderError(ValueError):
    """Raised when an audit cannot be validated, rendered, or safely written."""


class _TraceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.nodes: list[tuple[str, str | None]] = []
        self.edges: list[str] = []
        self.claims: list[str] = []
        self.feedback_targets: list[str] = []
        self.hunks: list[str] = []
        self.graph_ids: list[str] = []
        self.run_ids: list[str] = []
        self.audit_hashes: list[str] = []
        self.external_references: list[str] = []
        self.tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        values = {key: value for key, value in attrs}
        node_id = values.get("data-node-id")
        if node_id:
            self.nodes.append((node_id, values.get("data-fingerprint")))
        for key, target in (
            ("data-edge-id", self.edges),
            ("data-claim-id", self.claims),
            ("data-feedback-for", self.feedback_targets),
            ("data-hunk-id", self.hunks),
            ("data-graph-id", self.graph_ids),
            ("data-run-id", self.run_ids),
            ("data-audit-sha256", self.audit_hashes),
        ):
            value = values.get(key)
            if value:
                target.append(value)
        for key in ("href", "src"):
            value = values.get(key)
            if value and value.lstrip().lower().startswith(("http://", "https://", "//")):
                self.external_references.append(value)


def _resource_text(package: str, relative_path: str) -> str:
    return files(package).joinpath(relative_path).read_text(encoding="utf-8")


def _source_ref_label(value: str) -> str:
    """Keep exact refs in audit.json while making long commit ranges readable."""
    if ".." in value:
        left, right = value.split("..", 1)
        if re.fullmatch(r"[0-9a-fA-F]{12,}", left) and re.fullmatch(
            r"[0-9a-fA-F]{12,}", right
        ):
            return f"{left[:8]}..{right[:8]}"
    return value if len(value) <= 72 else f"{value[:69]}..."


def _as_hunk_view(
    hunk: ParsedHunk,
    *,
    line_side: str,
    highlight_lines: list[int],
) -> dict[str, Any]:
    highlights = set(highlight_lines)
    indexed_lines = list(enumerate(hunk.lines))
    if len(indexed_lines) <= FULL_HUNK_LINE_LIMIT:
        windows = [(0, len(indexed_lines))]
    else:
        # Excerpting is view-only: audit.json retains the complete trusted hunk.
        # Every hit gets a fixed context window and overlapping windows merge.
        hit_indexes = [
            index
            for index, line in indexed_lines
            if (line.old_number if line_side == "old" else line.new_number) in highlights
        ]
        windows = []
        for index in hit_indexes:
            start = max(0, index - HUNK_EXCERPT_CONTEXT_LINES)
            end = min(len(indexed_lines), index + HUNK_EXCERPT_CONTEXT_LINES + 1)
            if windows and start <= windows[-1][1]:
                windows[-1] = (windows[-1][0], max(windows[-1][1], end))
            else:
                windows.append((start, end))

    visible_lines: list[dict[str, Any]] = []
    cursor = 0
    displayed_line_count = 0
    for start, end in windows:
        if start > cursor:
            visible_lines.append({"kind": "omitted", "omitted_count": start - cursor})
        for _, line in indexed_lines[start:end]:
            active_number = line.old_number if line_side == "old" else line.new_number
            visible_lines.append(
                {
                    "kind": line.kind,
                    "prefix": line.prefix,
                    "content": line.content,
                    "old_number": line.old_number,
                    "new_number": line.new_number,
                    "highlighted": active_number in highlights,
                }
            )
            displayed_line_count += 1
        cursor = end
    if cursor < len(indexed_lines):
        visible_lines.append(
            {"kind": "omitted", "omitted_count": len(indexed_lines) - cursor}
        )

    return {
        "header": hunk.header,
        "lines": visible_lines,
        "displayed_line_count": displayed_line_count,
        "total_line_count": len(indexed_lines),
        "is_excerpt": displayed_line_count < len(indexed_lines),
    }


def _build_context(
    audit: Mapping[str, Any], *, source_audit_sha256: str
) -> dict[str, Any]:
    data = copy.deepcopy(dict(audit))
    runs = data["runs"]
    nodes = data["nodes"]
    edges = data["edges"]
    summary = data["summary"]
    source_provenance = (
        data["source"].get("extensions", {}).get("evidentloop", {})
    )
    demo_replay = source_provenance.get("execution_mode") == "demo_replay"
    current_run = runs[-1] if runs else None
    node_by_id = {node["id"]: node for node in nodes}
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        outgoing[edge["from"]].append(edge)

    changes: list[dict[str, Any]] = []
    if current_run:
        for edge in outgoing[current_run["id"]]:
            if edge["type"] != "contains_change":
                continue
            change = copy.deepcopy(node_by_id[edge["to"]])
            change["_edge_id"] = edge["id"]
            changes.append(change)
    if not changes:
        changes = [copy.deepcopy(node) for node in nodes if node["type"] == "change"]
        for change in changes:
            change["_edge_id"] = None

    change_ids = {change["id"] for change in changes}
    files_view: list[dict[str, Any]] = []
    seen_files: set[str] = set()
    for edge in edges:
        if edge["type"] != "changes_file" or edge["from"] not in change_ids:
            continue
        if edge["to"] in seen_files:
            continue
        file_node = copy.deepcopy(node_by_id[edge["to"]])
        file_node["_edge_id"] = edge["id"]
        files_view.append(file_node)
        seen_files.add(edge["to"])

    claims: list[dict[str, Any]] = []
    for owner in runs + changes:
        summary_audit = owner.get("summary_audit")
        if not summary_audit:
            continue
        claims.extend(
            {"owner_id": owner["id"], "claim": claim}
            for claim in summary_audit.get("claims", [])
        )

    finding_nodes = [node for node in nodes if node["type"] == "finding"]
    severity_labels = {"high": "高", "medium": "中", "low": "低", "note": "提示"}
    finding_status_labels = {"open": "待处理", "fixed": "已修复", "dismissed": "已忽略"}
    disposition_labels = {"accept": "确认有效", "false_positive": "误报"}
    line_side_labels = {"old": "旧文件", "new": "新文件"}
    finding_views: list[dict[str, Any]] = []
    for finding in finding_nodes:
        related = outgoing[finding["id"]]
        evidence_links = [
            {"edge_id": edge["id"], "node": node_by_id[edge["to"]]}
            for edge in related
            if edge["type"] == "supported_by_evidence"
        ]
        fix_links = [
            {"edge_id": edge["id"], "node": node_by_id[edge["to"]]}
            for edge in related
            if edge["type"] == "requires_fix"
        ]
        file_edge = next(
            (edge for edge in related if edge["type"] == "finding_in_file"),
            None,
        )
        extension = finding.get("extensions", {}).get("evidentloop", {})
        model_judgment = finding.get(
            "model_judgment",
            {"status": finding["status"], "severity": finding["severity"]},
        )
        human_adjudication = finding.get("human_adjudication") or {}
        hunk_view = (
            _as_hunk_view(
                parse_hunk(finding["hunk"]),
                line_side=finding["line_side"],
                highlight_lines=finding["highlight_lines"],
            )
            if finding.get("hunk")
            else None
        )
        finding_views.append(
            {
                "node": finding,
                "evidence_links": evidence_links,
                "fix_links": fix_links,
                "file_edge_id": file_edge["id"] if file_edge else None,
                "hunk_view": hunk_view,
                "unanchored": (
                    extension.get("unscored") is True
                    or extension.get("downgraded_from") == "bug"
                ),
                "severity_label": severity_labels[finding["severity"]],
                "status_label": finding_status_labels[finding["status"]],
                "model_severity_label": severity_labels[model_judgment["severity"]],
                "model_status_label": finding_status_labels[model_judgment["status"]],
                "human_adjudication": human_adjudication,
                "human_disposition_label": disposition_labels.get(
                    human_adjudication.get("disposition")
                ),
                "human_severity_label": severity_labels.get(
                    human_adjudication.get("severity_override")
                ),
                "line_side_label": line_side_labels.get(finding.get("line_side"), ""),
            }
        )

    category_labels = {
        "bug": "缺陷",
        "risk": "风险",
        "quality": "质量",
        "scope": "范围",
    }
    finding_groups: list[dict[str, Any]] = []
    next_number = 2
    for category in ("bug", "risk", "quality", "scope"):
        group = [view for view in finding_views if view["node"]["category"] == category]
        if group:
            finding_groups.append(
                {
                    "category": category,
                    "label": category_labels[category],
                    "number": next_number,
                    "findings": group,
                }
            )
            next_number += 1

    evidence_view: list[dict[str, Any]] = []
    for node in nodes:
        if node["type"] != "evidence":
            continue
        item = copy.deepcopy(node)
        item["_related_findings"] = [
            edge["from"]
            for edge in edges
            if edge["type"] == "supported_by_evidence" and edge["to"] == node["id"]
        ]
        item["_source_label"] = {
            "host_llm": "宿主语义审查",
            "test": "测试",
            "lint": "静态检查",
            "typecheck": "类型检查",
            "security_scan": "安全扫描",
        }.get(item["source"], item["source"])
        item["_status_label"] = {
            "pass": "通过",
            "fail": "发现问题",
            "error": "错误",
            "skipped": "已跳过",
        }.get(item["status"], item["status"])
        evidence_view.append(item)

    fixes_view: list[dict[str, Any]] = []
    for node in nodes:
        if node["type"] != "fix":
            continue
        item = copy.deepcopy(node)
        item["_source_findings"] = [
            edge["from"]
            for edge in edges
            if edge["type"] == "requires_fix" and edge["to"] == node["id"]
        ]
        item["_status_label"] = {
            "open": "待处理",
            "done": "已完成",
            "deferred": "已延期",
            "wont_fix": "不修复",
        }.get(item["status"], item["status"])
        fixes_view.append(item)

    status_copy = {
        "not_reviewed": (
            "审查尚未执行",
            "没有宿主审查依据，不能把零问题解读为干净结果。",
            "warning",
        ),
        "complete": (
            "审查输出已完整接收",
            "这只表示审查者输出满足结构契约，不代表上下文覆盖充分；请结合结论、问题与未计分项人工判断。",
            "clean" if summary["verdict"] == "pass_candidate" else "warning",
        ),
        "partial": (
            "审查仅部分完成",
            "已有问题可以查看，但本轮不能作为完整或干净结论。",
            "warning",
        ),
        "failed": (
            "审查失败",
            "报告保留失败状态，不把缺失 finding 包装为通过。",
            "failure",
        ),
    }
    status_heading, status_message, status_callout_class = status_copy[summary["review_status"]]
    if summary["verdict"] == "needs_human_triage":
        status_message = "本轮只有未精确锚定的语义风险，无法可靠计算数字风险分。"
        status_callout_class = "warning"

    verdict_labels = {
        "pass_candidate": "候选通过",
        "concerns": "存在待处理问题",
        "needs_human_triage": "需要人工分诊",
        "inconclusive": "结论不充分",
    }
    is_feedback_revision = summary.get("basis") == "human_adjudication"
    model_verdict = summary.get("model_verdict", summary["verdict"])
    model_risk_score = summary.get("model_risk_score", summary["risk_score"])
    human_findings = [
        view for view in finding_views if view["human_adjudication"]
    ]
    revision = (
        current_run.get("revision")
        if current_run and current_run.get("kind") == "feedback_revision"
        else None
    )
    run_views = []
    for run in runs:
        run_revision = run.get("revision") or {}
        run_views.append(
            {
                "run": run,
                "kind_label": (
                    "人工反馈修订"
                    if run.get("kind") == "feedback_revision"
                    else "模型审查"
                ),
                "source_run_id": run_revision.get("source_run_id"),
                "source_audit_sha256": run_revision.get("source_audit_sha256"),
                "feedback_sha256": run_revision.get("feedback_sha256"),
                "feedback_count": len(run_revision.get("events", [])),
            }
        )
    summary_audit_status = summary.get("summary_audit_status", "not_audited")
    summary_audit_labels = {
        "supported": "变更目标：已验证",
        "challenged": "变更目标：存在偏差",
        "partial": "变更目标：部分达成",
        "not_audited": "变更目标：未审计",
    }
    summary_audit_badge_classes = {
        "supported": "ok",
        "challenged": "risk",
        "partial": "warn",
        "not_audited": "soft",
    }
    score = summary["risk_score"]
    if score is None:
        risk_score_label = "无法可靠评分"
        risk_badge_label = "不适用"
        risk_badge_class = "warn"
    else:
        risk_score_label = str(score)
        if score >= 60:
            risk_badge_label, risk_badge_class = "高", "risk"
        elif score >= 25:
            risk_badge_label, risk_badge_class = "中", "warn"
        else:
            risk_badge_label, risk_badge_class = "低", "ok"

    has_run_history = len(runs) > 1
    fixes_section_number = next_number
    history_section_number = fixes_section_number + (1 if fixes_view else 0)
    evidence_section_number = history_section_number + (1 if has_run_history else 0)
    title = current_run["label"] if current_run else data["source"].get("description", "Audit Report")
    return {
        "audit": data,
        "summary": summary,
        "source_audit_sha256": source_audit_sha256,
        "current_run": current_run,
        "title": title,
        "source_ref_label": _source_ref_label(str(data["source"]["ref"])),
        "demo_replay": demo_replay,
        "demo_fixture_id": source_provenance.get("fixture_id"),
        "changes": changes,
        "primary_change": changes[0] if changes else None,
        "files": files_view,
        "claims": claims,
        "finding_groups": finding_groups,
        "human_findings": human_findings,
        "human_disposition_count": sum(
            "disposition" in view["human_adjudication"] for view in human_findings
        ),
        "human_comment_count": sum(
            "comment" in view["human_adjudication"] for view in human_findings
        ),
        "human_severity_count": sum(
            "severity_override" in view["human_adjudication"]
            for view in human_findings
        ),
        "is_feedback_revision": is_feedback_revision,
        "revision": revision,
        "run_views": run_views,
        "model_verdict_label": verdict_labels[model_verdict],
        "model_risk_score_label": (
            "无法可靠评分" if model_risk_score is None else str(model_risk_score)
        ),
        "feedback_target_count": len(finding_views),
        "fixes": fixes_view,
        "evidence": evidence_view,
        "next_section_number": next_number,
        "fixes_section_number": fixes_section_number,
        "history_section_number": history_section_number,
        "evidence_section_number": evidence_section_number,
        "has_run_history": has_run_history,
        "run_status_labels": {
            "pass_candidate": "候选通过",
            "concerns": "存在待处理问题",
            "needs_human_triage": "需要人工分诊",
            "inconclusive": "结论不充分",
        },
        "review_status_labels": {
            "not_reviewed": "未审查",
            "complete": "输出完整",
            "partial": "部分完成",
            "failed": "失败",
        },
        "verdict_label": verdict_labels[summary["verdict"]],
        "risk_score_label": risk_score_label,
        "risk_badge_label": risk_badge_label,
        "risk_badge_class": risk_badge_class,
        "summary_audit_label": summary_audit_labels[summary_audit_status],
        "summary_audit_badge_class": summary_audit_badge_classes[summary_audit_status],
        "claim_status_labels": {
            "supported": "已支持",
            "challenged": "有偏差",
            "partial": "部分支持",
            "unknown": "未知",
        },
        "change_type_labels": {
            "added": "新增",
            "modified": "修改",
            "deleted": "删除",
            "renamed": "重命名",
            "binary": "二进制",
        },
        "status_heading": status_heading,
        "status_message": status_message,
        "status_callout_class": status_callout_class,
        "renderer_version": RENDERER_VERSION,
    }


def validate_html_trace(
    html: str,
    audit: Mapping[str, Any],
    *,
    source_audit_sha256: str | None = None,
) -> list[str]:
    """Validate HTML identity, trace targets, and self-contained resource policy."""
    parser = _TraceParser()
    parser.feed(html)
    parser.close()
    errors: list[str] = []
    runs = audit["runs"]
    entities = {item["id"]: item for item in runs + audit["nodes"]}
    edge_ids = {edge["id"] for edge in audit["edges"]}
    claim_ids = {
        claim["id"]
        for entity in runs + audit["nodes"]
        for claim in entity.get("summary_audit", {}).get("claims", [])
    }
    finding_by_id = {
        node["id"]: node for node in audit["nodes"] if node["type"] == "finding"
    }
    hunk_ids = {
        node["hunk_id"]
        for node in finding_by_id.values()
        if node.get("hunk_id")
    }

    for node_id, fingerprint in parser.nodes:
        if node_id not in entities:
            errors.append(f"data-node-id points to unknown entity: {node_id}")
        if fingerprint is not None:
            finding = finding_by_id.get(node_id)
            if finding is None or finding["fingerprint"] != fingerprint:
                errors.append(f"data-fingerprint mismatch for {node_id}")
    for edge_id in parser.edges:
        if edge_id not in edge_ids:
            errors.append(f"data-edge-id points to unknown edge: {edge_id}")
    for claim_id in parser.claims:
        if claim_id not in claim_ids:
            errors.append(f"data-claim-id points to unknown claim: {claim_id}")
    for target_id in parser.feedback_targets:
        if target_id not in finding_by_id:
            errors.append(f"data-feedback-for points to unknown finding: {target_id}")
    for hunk_id in parser.hunks:
        if hunk_id not in hunk_ids:
            errors.append(f"data-hunk-id points to unknown hunk: {hunk_id}")

    rendered_node_ids = {node_id for node_id, _ in parser.nodes}
    rendered_finding_pairs = set(parser.nodes)
    for finding_id, finding in finding_by_id.items():
        if finding_id not in rendered_node_ids:
            errors.append(f"HTML is missing finding node: {finding_id}")
        if (finding_id, finding["fingerprint"]) not in rendered_finding_pairs:
            errors.append(f"HTML is missing finding fingerprint: {finding_id}")

    missing_claims = claim_ids.difference(parser.claims)
    for claim_id in sorted(missing_claims):
        errors.append(f"HTML is missing claim: {claim_id}")
    missing_hunks = hunk_ids.difference(parser.hunks)
    for hunk_id in sorted(missing_hunks):
        errors.append(f"HTML is missing anchored hunk: {hunk_id}")
    missing_feedback = set(finding_by_id).difference(parser.feedback_targets)
    for finding_id in sorted(missing_feedback):
        errors.append(f"HTML is missing feedback target: {finding_id}")
    if parser.graph_ids != [audit["graph_id"]]:
        errors.append("HTML must contain exactly one matching data-graph-id")
    expected_run_ids = [runs[-1]["id"]] if runs else []
    if parser.run_ids != expected_run_ids:
        errors.append("HTML data-run-id does not match the latest run")
    if len(parser.audit_hashes) != 1 or not re.fullmatch(
        r"sha256:[0-9a-f]{64}", parser.audit_hashes[0] if parser.audit_hashes else ""
    ):
        errors.append("HTML must contain exactly one valid data-audit-sha256")
    elif source_audit_sha256 and parser.audit_hashes != [source_audit_sha256]:
        errors.append("HTML data-audit-sha256 does not match audit.json bytes")
    if parser.external_references:
        errors.append("HTML contains remote href/src references")
    for required_tag in ("html", "head", "body", "main"):
        if required_tag not in parser.tags:
            errors.append(f"HTML is missing required <{required_tag}> element")
    return errors


def render_audit_data(
    audit: Mapping[str, Any], *, source_audit_sha256: str | None = None
) -> str:
    """Render an in-memory audit after structural and semantic validation.

    Use ``render_audit_file`` when feedback must bind to exact ``audit.json`` bytes.
    """
    try:
        assert_valid_audit(audit)
        if source_audit_sha256 is None:
            canonical = (
                json.dumps(audit, ensure_ascii=False, indent=2) + "\n"
            ).encode("utf-8")
            source_audit_sha256 = f"sha256:{hashlib.sha256(canonical).hexdigest()}"
        context = _build_context(
            audit, source_audit_sha256=source_audit_sha256
        )
        context["trusted_css"] = _resource_text(
            "evidentloop.renderers", "static/audit.css"
        )
        context["trusted_js"] = _resource_text(
            "evidentloop.renderers", "static/audit.js"
        )
        template_source = _resource_text(
            "evidentloop.renderers", "templates/audit.html.j2"
        )
        environment = Environment(
            autoescape=True,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        html = environment.from_string(template_source).render(**context)
    except (AuditValidationError, TemplateError, OSError, ValueError) as exc:
        raise AuditRenderError(str(exc)) from exc

    trace_errors = validate_html_trace(
        html, audit, source_audit_sha256=source_audit_sha256
    )
    if trace_errors:
        raise AuditRenderError("; ".join(trace_errors))
    return html


def render_audit_file(input_path: str | Path, output_path: str | Path) -> Path:
    """Validate and atomically replace one explicitly selected HTML output."""
    source = Path(input_path)
    target = Path(output_path)
    try:
        if source.resolve() == target.resolve():
            raise AuditRenderError("output HTML must not replace the input audit.json")
        source_raw = source.read_bytes()
        audit = json.loads(source_raw.decode("utf-8"))
    except AuditRenderError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuditRenderError(f"cannot read valid audit JSON: {exc}") from exc

    source_hash = f"sha256:{hashlib.sha256(source_raw).hexdigest()}"
    html = render_audit_data(audit, source_audit_sha256=source_hash)
    candidate: Path | None = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{target.name}.",
            suffix=".tmp",
            dir=target.parent,
            delete=False,
        ) as handle:
            handle.write(html)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            candidate = Path(handle.name)
        os.replace(candidate, target)
    except OSError as exc:
        if candidate is not None:
            candidate.unlink(missing_ok=True)
        raise AuditRenderError(f"cannot atomically replace output HTML: {exc}") from exc
    return target
