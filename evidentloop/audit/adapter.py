"""ReviewResult to code-diff Audit Graph adapter."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Mapping

from evidentloop.renderers.hunk import parse_hunk
from evidentloop.review.schema import Finding, ReviewResult, ReviewStatus
from evidentloop.validation import SCHEMA_VERSION


SEVERITY_WEIGHTS: dict[str, int] = {
    "high": 40,
    "medium": 20,
    "low": 8,
    "note": 2,
}

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


def _normalize_candidate_path(value: str | None, trusted_paths: set[str]) -> tuple[str | None, str]:
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


def _fingerprint(*, category: str, file_path: str | None, anchor: str, title: str) -> str:
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
) -> dict[str, Any]:
    """Build a fully mechanical, schema-ready code-diff audit graph."""
    trusted_paths = {str(item["path"]) for item in skeleton["files"]}
    hunks = [item for item in hunk_index["hunks"] if isinstance(item, Mapping)]
    nodes: list[dict[str, Any]] = [dict(skeleton["change"])]
    edges: list[dict[str, Any]] = [
        {"id": "edge-001", "type": "contains_change", "from": skeleton["run"]["id"], "to": skeleton["change"]["id"]}
    ]
    file_ids: dict[str, str] = {}
    edge_index = 2
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

    scored: list[dict[str, Any]] = []
    unscored = 0
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
        is_unscored = False
        if category == "bug" and anchor is None:
            category = "risk"
            severity = "medium" if severity in {"high", "medium"} else severity
            extensions.update(
                {
                    "downgraded_from": "bug",
                    "downgrade_reason": anchor_reason,
                    "unscored": True,
                }
            )
            is_unscored = True
        elif trusted_file_path is None:
            extensions.update({"anchor_reason": anchor_reason, "unscored": True})
            is_unscored = True
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

        if is_unscored:
            unscored += 1
        else:
            scored.append(finding_node)

    status = _review_status(review_result)
    finding_count = len(review_result.findings)
    advisory_verdict = review_result.advisory_verdict.verdict.value
    if status != "complete":
        verdict = "inconclusive"
        risk_score: int | None = None
    elif finding_count == 0:
        # A structurally complete reviewer response is not automatically a
        # clean result; preserve the core coverage/evidence adjudication.
        if advisory_verdict == "pass_candidate":
            verdict = "pass_candidate"
            risk_score = 0
        else:
            verdict = "inconclusive"
            risk_score = None
    elif advisory_verdict == "inconclusive":
        verdict = "inconclusive"
        risk_score = None
    elif scored:
        verdict = "concerns"
        risk_score = min(sum(SEVERITY_WEIGHTS[item["severity"]] for item in scored), 100)
    else:
        verdict = "needs_human_triage"
        risk_score = None

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
    if status == "complete" and overall_assessment:
        run["summary"] = overall_assessment
    else:
        run["summary"] = (
            "宿主审查已完成，未报告 finding。"
            if status == "complete" and finding_count == 0
            else f"宿主审查生成 {finding_count} 条 finding，状态为 {status}。"
        )
    summary = {
        "review_status": status,
        "verdict": verdict,
        "risk_score": risk_score,
        "finding_count": finding_count,
        "unscored_finding_count": unscored,
        "open_finding_count": finding_count,
        "fix_count": 0,
        "fix_done_count": 0,
        "summary_audit_status": "not_audited",
        "extensions": {"evidentloop": {"review_diagnostics": diagnostics}},
    }
    audit = {
        "schema_version": SCHEMA_VERSION,
        "graph_id": skeleton["graph_id"],
        "source": dict(skeleton["source"]),
        "runs": [run],
        "nodes": nodes,
        "edges": edges,
        "summary": summary,
        "extensions": {
            "evidentloop": {
                "profile": "code_diff",
                "run_id": skeleton["run_id"],
                "adapter": "gitdiff/v0",
                "reviewer_prompt": dict(skeleton.get("reviewer_prompt") or {}),
            }
        },
    }
    return audit
