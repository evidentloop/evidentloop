"""ReviewResult to code-diff Audit Graph adapter."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence

from evidentloop.audit.summary import build_summary, needs_human_triage
from evidentloop.renderers.hunk import parse_hunk
from evidentloop.review.claims import aggregate_claim_status
from evidentloop.review.schema import Finding, ReviewResult, ReviewStatus
from evidentloop.validation import SCHEMA_VERSION
from evidentloop.versions import diff_version_from_fingerprint


_BUG_CATEGORIES = {"bug", "logic_error", "semantic_equivalence", "correctness"}
_RISK_CATEGORIES = {
    "security",
    "performance",
    "possible_bug",
    "missing_validation",
    "error_handling",
}
_QUALITY_CATEGORIES = {
    "quality",
    "maintainability",
    "missing_test",
    "style",
    "suggestion",
    "documentation",
    "testing",
}
_SCOPE_CATEGORIES = {"scope", "spec_mismatch"}


@dataclass(frozen=True)
class ResolvedAnchor:
    """Trusted location resolved from the hunk index."""

    file_path: str
    hunk_id: str
    snippet: str
    start_line: int
    end_line: int
    line_side: str
    highlight_lines: tuple[int, ...]


def _audit_category(category: str) -> str:
    if category in _BUG_CATEGORIES:
        return "bug"
    if category in _RISK_CATEGORIES:
        return "risk"
    if category in _QUALITY_CATEGORIES:
        return "quality"
    if category in _SCOPE_CATEGORIES:
        return "scope"
    return "quality"


def _normalize_candidate_path(
    value: str | None, trusted_paths: set[str]
) -> tuple[str | None, str]:
    if not value or "\x00" in value or "\\" in value:
        return None, "missing_or_unsafe_file_path"
    candidate = value.strip().removeprefix("./")
    path = PurePosixPath(candidate)
    if path.is_absolute() or ".." in path.parts:
        return None, "unsafe_file_path"
    if candidate in trusted_paths:
        return candidate, "trusted"
    if candidate.startswith(("a/", "b/")) and candidate[2:] in trusted_paths:
        return candidate[2:], "trusted"
    return None, "file_not_in_diff"


def _entry_supports_line(entry: Mapping[str, Any], line: int) -> tuple[str, int] | None:
    parsed = parse_hunk(str(entry["snippet"]))
    # Exact finding anchors must identify a changed line. Context lines are
    # useful evidence around a finding, but highlighting one as the cause would
    # misrepresent unchanged code as the modification under review.
    for parsed_line in parsed.lines:
        if parsed_line.kind == "add" and parsed_line.new_number == line:
            return "new", line
    for parsed_line in parsed.lines:
        if parsed_line.kind == "delete" and parsed_line.old_number == line:
            return "old", line
    return None


def _default_changed_line(entry: Mapping[str, Any]) -> tuple[str, int] | None:
    parsed = parse_hunk(str(entry["snippet"]))
    for line in parsed.lines:
        if line.kind == "add" and line.new_number is not None:
            return "new", line.new_number
    for line in parsed.lines:
        if line.kind == "delete" and line.old_number is not None:
            return "old", line.old_number
    return None


def _resolve_anchor(
    finding: Finding,
    *,
    trusted_paths: set[str],
    hunks: list[Mapping[str, Any]],
) -> tuple[ResolvedAnchor | None, str, str | None]:
    file_path, file_reason = _normalize_candidate_path(finding.file, trusted_paths)
    if file_path is None:
        return None, file_reason, None

    candidates = [entry for entry in hunks if entry["file_path"] == file_path]
    header = finding.diff_hunk.strip() if finding.diff_hunk else None
    if header:
        header_matches = [entry for entry in candidates if entry["header"] == header]
        if not header_matches:
            return None, "header_not_in_trusted_hunk", file_path
        candidates = header_matches

    chosen: Mapping[str, Any] | None = None
    side_and_line: tuple[str, int] | None = None
    if finding.line is not None:
        line_matches: list[tuple[Mapping[str, Any], tuple[str, int]]] = []
        for entry in candidates:
            matched = _entry_supports_line(entry, finding.line)
            if matched is not None:
                line_matches.append((entry, matched))
        if len(line_matches) == 1:
            chosen, side_and_line = line_matches[0]
        elif not line_matches:
            return None, "line_outside_trusted_hunk", file_path
        else:
            return None, "ambiguous_hunk", file_path
    elif header and len(candidates) == 1:
        chosen = candidates[0]
        side_and_line = _default_changed_line(chosen)
        if side_and_line is None:
            return None, "hunk_has_no_changed_line", file_path
    else:
        return None, "missing_exact_anchor", file_path

    assert chosen is not None and side_and_line is not None
    side, line = side_and_line
    return (
        ResolvedAnchor(
            file_path=file_path,
            hunk_id=str(chosen["hunk_id"]),
            snippet=str(chosen["snippet"]),
            start_line=line,
            end_line=line,
            line_side=side,
            highlight_lines=(line,),
        ),
        "trusted",
        file_path,
    )


def _fingerprint(
    *, category: str, file_path: str | None, anchor: str, title: str
) -> str:
    canonical = "\n".join(
        [
            SCHEMA_VERSION,
            file_path or "<unanchored>",
            category,
            anchor,
            " ".join(title.casefold().split()),
        ]
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def _review_status(result: ReviewResult) -> str:
    if result.review_status == ReviewStatus.COMPLETE:
        return "complete"
    if result.review_status == ReviewStatus.TRUNCATED:
        return "partial"
    return "failed"


def build_audit_graph(
    *,
    review_result: ReviewResult,
    skeleton: Mapping[str, Any],
    hunk_index: Mapping[str, Any],
    overall_assessment: str | None = None,
    change_summary: Mapping[str, Any] | None = None,
    fix_verification_results: Sequence[Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    """Build a fully mechanical, schema-ready code-diff audit graph."""
    trusted_paths = {str(item["path"]) for item in skeleton["files"]}
    hunks = [item for item in hunk_index["hunks"] if isinstance(item, Mapping)]
    primary_change = dict(skeleton["change"])
    if change_summary is not None:
        primary_change["summary"] = str(change_summary["overview"])
        primary_extensions = dict(primary_change.get("extensions") or {})
        primary_evidentloop = dict(primary_extensions.get("evidentloop") or {})
        primary_evidentloop["review_focus"] = str(change_summary["review_focus"])
        primary_extensions["evidentloop"] = primary_evidentloop
        primary_change["extensions"] = primary_extensions

    nodes: list[dict[str, Any]] = [primary_change]
    edges: list[dict[str, Any]] = [
        {
            "id": "edge-001",
            "type": "contains_change",
            "from": skeleton["run"]["id"],
            "to": skeleton["change"]["id"],
        }
    ]
    file_ids: dict[str, str] = {}
    edge_index = 2
    if change_summary is not None:
        for index, theme in enumerate(change_summary["themes"], start=2):
            change_id = f"change-{index:03d}"
            nodes.append(
                {
                    "id": change_id,
                    "type": "change",
                    "title": str(theme["title"]),
                    "summary": str(theme["summary"]),
                    "extensions": {"evidentloop": {"impact": str(theme["impact"])}},
                }
            )
            edges.append(
                {
                    "id": f"edge-{edge_index:03d}",
                    "type": "contains_change",
                    "from": skeleton["run"]["id"],
                    "to": change_id,
                }
            )
            edge_index += 1

    for item in skeleton["files"]:
        node = dict(item)
        nodes.append(node)
        file_ids[node["path"]] = node["id"]
        edges.append(
            {
                "id": f"edge-{edge_index:03d}",
                "type": "changes_file",
                "from": skeleton["change"]["id"],
                "to": node["id"],
            }
        )
        edge_index += 1

    for index, review_finding in enumerate(review_result.findings, start=1):
        finding_id = f"finding-{index:03d}"
        evidence_id = f"evidence-{index:03d}"
        category = _audit_category(review_finding.category)
        anchor, anchor_reason, trusted_file_path = _resolve_anchor(
            review_finding,
            trusted_paths=trusted_paths,
            hunks=hunks,
        )
        extensions: dict[str, Any] = {
            "review_finding_id": review_finding.id,
            "original_category": review_finding.category,
            "confidence": review_finding.confidence.value,
        }
        severity = review_finding.severity.value
        if category == "bug" and anchor is None:
            category = "risk"
            severity = "medium" if severity in {"high", "medium"} else severity
            extensions.update(
                {
                    "downgraded_from": "bug",
                    "downgrade_reason": anchor_reason,
                }
            )
        elif trusted_file_path is None:
            extensions["anchor_reason"] = anchor_reason
        elif anchor is None and review_finding.locatability.value == "exact":
            extensions["anchor_reason"] = anchor_reason

        fingerprint = _fingerprint(
            category=category,
            file_path=trusted_file_path,
            anchor=anchor.hunk_id if anchor else (trusted_file_path or anchor_reason),
            title=review_finding.summary,
        )
        finding_node: dict[str, Any] = {
            "id": finding_id,
            "type": "finding",
            "category": category,
            "severity": severity,
            "status": "open",
            "title": review_finding.summary,
            "detail": review_finding.detail,
            "fingerprint": fingerprint,
            "model_judgment": {"status": "open", "severity": severity},
            "extensions": {"evidentloop": extensions},
        }
        if trusted_file_path is not None:
            finding_node["file_path"] = trusted_file_path
        if anchor is not None:
            finding_node.update(
                {
                    "hunk_id": anchor.hunk_id,
                    "start_line": anchor.start_line,
                    "end_line": anchor.end_line,
                    "line_side": anchor.line_side,
                    "highlight_lines": list(anchor.highlight_lines),
                    "hunk": anchor.snippet,
                }
            )
        nodes.append(finding_node)

        evidence_node = {
            "id": evidence_id,
            "type": "evidence",
            "source": "host_llm",
            "status": "fail",
            "summary": f"宿主语义审查结论：{review_finding.summary}",
            "detail": review_finding.detail,
        }
        nodes.append(evidence_node)
        if trusted_file_path is not None:
            edges.append(
                {
                    "id": f"edge-{edge_index:03d}",
                    "type": "finding_in_file",
                    "from": finding_id,
                    "to": file_ids[trusted_file_path],
                }
            )
            edge_index += 1
        edges.append(
            {
                "id": f"edge-{edge_index:03d}",
                "type": "supported_by_evidence",
                "from": finding_id,
                "to": evidence_id,
            }
        )
        edge_index += 1

    frozen_verification = skeleton.get("fix_verification")
    summary_audit: dict[str, Any] | None = None
    if fix_verification_results and isinstance(frozen_verification, Mapping):
        frozen_targets = {
            str(target["claim_id"]): target
            for target in frozen_verification.get("targets", [])
        }
        claims: list[dict[str, Any]] = []
        for result in fix_verification_results:
            claim_id = str(result["claim_id"])
            target = frozen_targets.get(claim_id)
            claim_status = str(result["status"])
            if target is None or claim_status not in {
                "supported",
                "challenged",
                "partial",
                "unknown",
            }:
                continue
            claims.append(
                {
                    "id": claim_id,
                    "text": str(target["claim"]),
                    "status": claim_status,
                    "reason": str(result["reason"]),
                }
            )
            if claim_status == "unknown":
                continue
            evidence_id = f"evidence-{claim_id}"
            nodes.append(
                {
                    "id": evidence_id,
                    "type": "evidence",
                    "source": "host_llm",
                    "status": "pass" if claim_status == "supported" else "fail",
                    "summary": str(result["evidence"]),
                }
            )
            edge_types = (
                ("supports_claim",)
                if claim_status == "supported"
                else ("challenges_claim",)
                if claim_status == "challenged"
                else ("supports_claim", "challenges_claim")
            )
            for edge_type in edge_types:
                edges.append(
                    {
                        "id": f"edge-{edge_index:03d}",
                        "type": edge_type,
                        "from": evidence_id,
                        "to": skeleton["run"]["id"],
                        "claim_id": claim_id,
                    }
                )
                edge_index += 1
        summary_audit = {
            "status": aggregate_claim_status([claim["status"] for claim in claims]),
            "claims": claims,
        }

    status = _review_status(review_result)
    finding_count = len(review_result.findings)
    advisory_verdict = review_result.advisory_verdict.verdict.value
    if status != "complete":
        verdict = "inconclusive"
    elif finding_count == 0:
        if advisory_verdict == "pass_candidate":
            verdict = "pass_candidate"
        else:
            verdict = "inconclusive"
    elif advisory_verdict == "inconclusive":
        verdict = "inconclusive"
    else:
        finding_nodes = [n for n in nodes if n["type"] == "finding"]
        trusted_finding_ids = {
            str(edge["from"])
            for edge in edges
            if edge["type"] == "finding_in_file"
        }
        if all(
            needs_human_triage(
                node,
                has_trusted_file_association=str(node["id"])
                in trusted_finding_ids,
            )
            for node in finding_nodes
        ):
            verdict = "needs_human_triage"
        else:
            verdict = "concerns"

    diagnostics = {
        "intent_coverage": review_result.intent_coverage.value,
        "files_reviewed": review_result.budget.files_reviewed,
        "files_total": review_result.budget.files_total,
        "pack_completeness": review_result.quality_metrics.pack_completeness,
        "raw_findings_count": review_result.quality_metrics.raw_findings_count,
        "emitted_findings_count": review_result.quality_metrics.emitted_findings_count,
        "reviewer_failure_reason": (
            review_result.reviewer.failure_reason.value
            if review_result.reviewer.failure_reason is not None
            else None
        ),
        "advisory_verdict": advisory_verdict,
        "advisory_rationale": review_result.advisory_verdict.rationale,
    }
    run = dict(skeleton["run"])
    run["status"] = verdict
    run["kind"] = "model_review"
    if summary_audit is not None:
        run["summary_audit"] = summary_audit
    if status == "complete" and overall_assessment:
        run["summary"] = overall_assessment
    else:
        run["summary"] = (
            "宿主审查已完成，未报告 finding。"
            if status == "complete" and finding_count == 0
            else f"宿主审查生成 {finding_count} 条 finding，状态为 {status}。"
        )
    calculated_summary = build_summary(
        [node for node in nodes if node["type"] == "finding"],
        [],
        review_status=status,
        empty_verdict="pass_candidate"
        if verdict == "pass_candidate"
        else "inconclusive",
        force_inconclusive=verdict == "inconclusive" and finding_count > 0,
        trusted_finding_ids={
            str(edge["from"])
            for edge in edges
            if edge["type"] == "finding_in_file"
        },
    )
    summary = {
        **calculated_summary,
        "summary_audit_status": (
            summary_audit["status"] if summary_audit is not None else "not_audited"
        ),
        "basis": "model_review",
        "extensions": {"evidentloop": {"review_diagnostics": diagnostics}},
    }
    evidentloop_extensions: dict[str, Any] = {
        "profile": "code_diff",
        "run_id": skeleton["run_id"],
        "adapter": "gitdiff/v0",
        "diff_version": diff_version_from_fingerprint(
            review_result.artifact_fingerprint
        ),
        "reviewer_prompt": dict(skeleton.get("reviewer_prompt") or {}),
    }
    if isinstance(frozen_verification, Mapping):
        evidentloop_extensions["fix_verification"] = dict(frozen_verification)
    audit = {
        "schema_version": SCHEMA_VERSION,
        "graph_id": skeleton["graph_id"],
        "source": dict(skeleton["source"]),
        "runs": [run],
        "nodes": nodes,
        "edges": edges,
        "summary": summary,
        "extensions": {"evidentloop": evidentloop_extensions},
    }
    return audit
