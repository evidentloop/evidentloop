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


RENDERER_VERSION = "0.4"
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
            if value and value.lstrip().lower().startswith(
                ("http://", "https://", "//")
            ):
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


def _evidence_adds_context(node: Mapping[str, Any], finding_title: str) -> bool:
    summary = str(node.get("summary") or "").strip()
    repeated_title = summary.removeprefix("宿主语义审查结论：").strip()
    return bool(summary and repeated_title != finding_title.strip())


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
            if (line.old_number if line_side == "old" else line.new_number)
            in highlights
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
    current_run = runs[-1] if runs else None
    model_run = next(
        (run for run in reversed(runs) if run.get("kind") == "model_review"),
        None,
    )
    node_by_id = {node["id"]: node for node in nodes}
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        outgoing[edge["from"]].append(edge)

    severity_labels = {"high": "高", "medium": "中", "low": "低", "note": "提示"}
    finding_status_labels = {"open": "待处理", "fixed": "已修复", "dismissed": "已忽略"}
    disposition_labels = {"accept": "确认有效", "false_positive": "误报"}
    verdict_labels = {
        "pass_candidate": "无待处理问题",
        "concerns": "存在待处理问题",
        "needs_human_triage": "需要人工分诊",
        "inconclusive": "结论不充分",
    }
    review_status_labels = {
        "not_reviewed": "未审查",
        "complete": "输出完整",
        "partial": "部分完成",
        "failed": "失败",
    }
    claim_status_labels = {
        "supported": "认可",
        "challenged": "不认可",
        "partial": "部分认可",
        "unknown": "暂无法判断",
    }
    change_type_labels = {
        "added": "新增",
        "modified": "修改",
        "deleted": "删除",
        "renamed": "重命名",
        "binary": "二进制",
    }

    changes: list[dict[str, Any]] = []
    if model_run:
        for edge in outgoing[model_run["id"]]:
            if edge["type"] == "contains_change":
                change = copy.deepcopy(node_by_id[edge["to"]])
                change["_edge_id"] = edge["id"]
                changes.append(change)
    if not changes:
        changes = [copy.deepcopy(node) for node in nodes if node["type"] == "change"]
        for change in changes:
            change["_edge_id"] = None

    change_ids = {change["id"] for change in changes}
    finding_nodes = [node for node in nodes if node["type"] == "finding"]
    finding_nodes_by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in finding_nodes:
        if finding.get("file_path"):
            finding_nodes_by_file[str(finding["file_path"])].append(finding)

    claim_findings: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        source = node_by_id.get(edge["from"])
        if (
            edge["type"] in {"supports_claim", "challenges_claim"}
            and edge.get("claim_id")
            and source
            and source["type"] == "finding"
        ):
            claim_findings[(edge["to"], edge["claim_id"])].append(source)

    files_view: list[dict[str, Any]] = []
    seen_files: set[str] = set()
    for edge in edges:
        if (
            edge["type"] != "changes_file"
            or edge["from"] not in change_ids
            or edge["to"] in seen_files
        ):
            continue
        file_node = copy.deepcopy(node_by_id[edge["to"]])
        file_node["_edge_id"] = edge["id"]
        related_findings = finding_nodes_by_file.get(file_node["path"], [])
        file_node["_finding_ids"] = [str(finding["id"]) for finding in related_findings]
        open_findings = [
            finding for finding in related_findings if finding["status"] == "open"
        ]
        if open_findings:
            file_node["_issue_link_id"] = open_findings[0]["id"]
            file_node["_issue_link_label"] = f"查看待处理问题（{len(open_findings)}）"
        elif related_findings:
            statuses = {finding["status"] for finding in related_findings}
            file_node["_issue_link_id"] = related_findings[0]["id"]
            if statuses == {"dismissed"}:
                state_label = "已忽略"
            elif statuses == {"fixed"}:
                state_label = "已修复"
            else:
                state_label = "已处理"
            file_node["_issue_link_label"] = (
                f"查看{state_label}问题（{len(related_findings)}）"
            )
        files_view.append(file_node)
        seen_files.add(edge["to"])

    primary_change = changes[0] if changes else None
    primary_change_extension = (
        primary_change.get("extensions", {}).get("evidentloop", {})
        if primary_change
        else {}
    )
    review_focus = primary_change_extension.get("review_focus")
    semantic_change_summary = (
        {
            "overview": primary_change,
            "review_focus": str(review_focus),
            "themes": [
                {
                    "node": change,
                    "impact": str(
                        change.get("extensions", {})
                        .get("evidentloop", {})
                        .get("impact", "")
                    ),
                }
                for change in changes[1:]
            ],
        }
        if review_focus and len(changes) > 1
        else None
    )
    change_stats = {
        "file_count": len(files_view),
        "additions": sum(int(item.get("additions") or 0) for item in files_view),
        "deletions": sum(int(item.get("deletions") or 0) for item in files_view),
        "binary_count": sum(item.get("change_type") == "binary" for item in files_view),
    }

    finding_views: list[dict[str, Any]] = []
    for finding in finding_nodes:
        related = outgoing[finding["id"]]
        evidence_links = [
            {"edge_id": edge["id"], "node": node_by_id[edge["to"]]}
            for edge in related
            if edge["type"] == "supported_by_evidence"
            and _evidence_adds_context(node_by_id[edge["to"]], finding["title"])
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
                "evidence_links": evidence_links,
                "fix_links": fix_links,
                "file_edge_id": file_edge["id"] if file_edge else None,
                "hunk_view": hunk_view,
                "line_side_label": {
                    "old": "旧文件",
                    "new": "新文件",
                }.get(finding.get("line_side"), ""),
                "unanchored": (
                    extension.get("downgraded_from") == "bug"
                    or not finding.get("file_path")
                ),
            }
        )

    evidentloop_extensions = data.get("extensions", {}).get("evidentloop", {})
    frozen_verification = evidentloop_extensions.get("fix_verification")
    fix_verification_view: dict[str, Any] | None = None
    if isinstance(frozen_verification, Mapping) and model_run:
        claims = {
            claim["id"]: claim
            for claim in model_run.get("summary_audit", {}).get("claims", [])
        }
        targets = []
        status_counts = {status: 0 for status in claim_status_labels}
        incomplete_count = 0
        for frozen_target in frozen_verification["targets"]:
            claim = claims.get(frozen_target["claim_id"])
            if claim is None:
                incomplete_count += 1
                targets.append(
                    {
                        "source": frozen_target,
                        "claim": None,
                        "status": "incomplete",
                        "status_label": "未完成",
                        "evidence": [],
                    }
                )
            else:
                claim_edges = [
                    edge
                    for edge in edges
                    if edge.get("claim_id") == claim["id"]
                    and edge["to"] == model_run["id"]
                    and edge["type"] in {"supports_claim", "challenges_claim"}
                ]
                evidence = [
                    {
                        "edge_id": edge["id"],
                        "edge_type": edge["type"],
                        "node": node_by_id[edge["from"]],
                    }
                    for edge in claim_edges
                ]
                status_counts[claim["status"]] += 1
                targets.append(
                    {
                        "source": frozen_target,
                        "claim": claim,
                        "status": claim["status"],
                        "status_label": claim_status_labels[claim["status"]],
                        "evidence": evidence,
                    }
                )
        fix_verification_view = {
            "source_report_version": frozen_verification["source_report_version"],
            "source_diff_version": frozen_verification["source_diff_version"],
            "owner_id": model_run["id"],
            "targets": targets,
            "incomplete_count": incomplete_count,
            "status_counts": [
                {
                    "status": status,
                    "label": label,
                    "count": status_counts[status],
                }
                for status, label in claim_status_labels.items()
                if status_counts[status]
            ],
        }

    change_claims: list[dict[str, Any]] = []
    if fix_verification_view is None:
        for owner in [*runs, *changes]:
            for claim in owner.get("summary_audit", {}).get("claims", []):
                related_findings = claim_findings.get((owner["id"], claim["id"]), [])
                related_state = None
                related_state_label = None
                if related_findings and not any(
                    finding["status"] == "open" for finding in related_findings
                ):
                    statuses = {finding["status"] for finding in related_findings}
                    if statuses == {"dismissed"}:
                        related_state = "dismissed"
                        related_state_label = "相关问题已忽略"
                    elif statuses == {"fixed"}:
                        related_state = "fixed"
                        related_state_label = "相关问题已修复"
                    else:
                        related_state = "handled"
                        related_state_label = "相关问题已处理"
                change_claims.append(
                    {
                        "owner_id": owner["id"],
                        "claim": claim,
                        "status_label": ("模型原判断" if related_state else "模型判断")
                        + f"：{claim_status_labels[claim['status']]}",
                        "related_state": related_state,
                        "related_state_label": related_state_label,
                    }
                )

    revision_runs = [run for run in runs if run.get("kind") == "feedback_revision"]
    feedback_history: list[dict[str, Any]] = []
    for index, run in enumerate(revision_runs):
        revision = run["revision"]
        before_summary = revision["source_summary"]
        after_summary = (
            revision_runs[index + 1]["revision"]["source_summary"]
            if index + 1 < len(revision_runs)
            else summary
        )
        summary_changes: list[dict[str, str]] = []
        if before_summary["verdict"] != after_summary["verdict"]:
            summary_changes.append(
                {
                    "label": "结论",
                    "before": verdict_labels[before_summary["verdict"]],
                    "after": verdict_labels[after_summary["verdict"]],
                }
            )
        if before_summary.get("overall_severity") != after_summary.get(
            "overall_severity"
        ):
            summary_changes.append(
                {
                    "label": "严重程度",
                    "before": severity_labels.get(
                        before_summary.get("overall_severity"), "无"
                    ),
                    "after": severity_labels.get(
                        after_summary.get("overall_severity"), "无"
                    ),
                }
            )
        if before_summary["open_finding_count"] != after_summary["open_finding_count"]:
            summary_changes.append(
                {
                    "label": "待处理问题",
                    "before": str(before_summary["open_finding_count"]),
                    "after": str(after_summary["open_finding_count"]),
                }
            )

        event_views: list[dict[str, Any]] = []
        for event in revision["events"]:
            action = event["action"]
            value: str | None = None
            if action == "comment":
                label = "删除评论" if event["comment"] is None else "更新评论"
                value = event["comment"]
            elif action == "severity_override":
                label = "恢复模型严重度" if event["severity"] is None else "调整严重度"
                value = severity_labels.get(event["severity"])
            else:
                label = {
                    "accept": "确认有效",
                    "false_positive": "标记误报",
                }[action]
            event_views.append(
                {
                    "target_title": node_by_id[event["target_id"]]["title"],
                    "label": label,
                    "value": value,
                }
            )

        feedback_history.append(
            {
                "run": run,
                "summary_changes": summary_changes,
                "events": event_views,
            }
        )

    overall_severity = summary.get("overall_severity")
    overall_severity_label = (
        "不适用"
        if overall_severity is None
        else severity_labels.get(overall_severity, overall_severity)
    )
    fix_truth_label = (
        "本轮未验证"
        if not isinstance(frozen_verification, Mapping)
        else "验证未完成"
        if fix_verification_view is None
        else " / ".join(
            [
                *(
                    f"{item['label']} {item['count']}"
                    for item in fix_verification_view["status_counts"]
                ),
                *(
                    [f"未完成 {fix_verification_view['incomplete_count']}"]
                    if fix_verification_view["incomplete_count"]
                    else []
                ),
            ]
        )
    )
    status_messages = {
        "not_reviewed": "未执行模型审查，不能把零问题理解为通过。",
        "partial": "只取得部分审查结果，本轮不能作为完整结论。",
        "failed": "审查失败；报告保留失败事实，不把缺失问题包装为通过。",
    }
    status_note = summary.get("notice") or status_messages.get(summary["review_status"])
    source_provenance = data["source"].get("extensions", {}).get("evidentloop", {})
    title = (
        model_run["label"]
        if model_run
        else data["source"].get("description", "Audit Report")
    )
    return {
        "audit": data,
        "summary": summary,
        "source_audit_sha256": source_audit_sha256,
        "current_run": current_run,
        "model_run": model_run,
        "title": title,
        "source_ref_label": _source_ref_label(str(data["source"]["ref"])),
        "changes": changes,
        "primary_change": primary_change,
        "semantic_change_summary": semantic_change_summary,
        "change_stats": change_stats,
        "files": files_view,
        "change_claims": change_claims,
        "findings": finding_views,
        "fix_verification_view": fix_verification_view,
        "feedback_history": feedback_history,
        "feedback_target_count": len(finding_views),
        "change_type_labels": change_type_labels,
        "claim_status_labels": claim_status_labels,
        "report_truth": {
            "review_status": review_status_labels[summary["review_status"]],
            "verdict": verdict_labels[summary["verdict"]],
            "overall_severity": overall_severity_label,
            "fix_verification": fix_truth_label,
            "status_note": status_note,
        },
        "demo_replay": source_provenance.get("execution_mode") == "demo_replay",
        "demo_fixture_id": source_provenance.get("fixture_id"),
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
        node["hunk_id"] for node in finding_by_id.values() if node.get("hunk_id")
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
            canonical = (json.dumps(audit, ensure_ascii=False, indent=2) + "\n").encode(
                "utf-8"
            )
            source_audit_sha256 = f"sha256:{hashlib.sha256(canonical).hexdigest()}"
        context = _build_context(audit, source_audit_sha256=source_audit_sha256)
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
