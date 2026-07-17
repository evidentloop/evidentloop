"""Structural and cross-object validation for ``audit.json``."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator

from .renderers.hunk import HunkParseError, parse_hunk


SCHEMA_VERSION = "0.4"


@dataclass(frozen=True)
class ValidationIssue:
    """Stable validation diagnostic with a JSON path and related IDs."""

    code: str
    path: str
    message: str
    related_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "path": self.path,
            "message": self.message,
            "related_ids": list(self.related_ids),
        }


class AuditValidationError(ValueError):
    """Raised when structural or semantic validation fails."""

    def __init__(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        summary = "; ".join(
            f"{issue.code} at {issue.path}: {issue.message}"
            for issue in self.issues[:5]
        )
        if len(self.issues) > 5:
            summary += f"; and {len(self.issues) - 5} more"
        super().__init__(summary)


def load_audit_schema() -> dict[str, Any]:
    """Load the packaged JSON Schema 2020-12 contract."""
    resource = files("evidentloop.schemas").joinpath(
        f"audit-v{SCHEMA_VERSION}.schema.json"
    )
    return json.loads(resource.read_text(encoding="utf-8"))


def _pointer(parts: Iterable[Any]) -> str:
    escaped = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(escaped) if escaped else "/"


def validate_structure(data: Any) -> list[ValidationIssue]:
    """Validate only the JSON Schema layer."""
    validator = Draft202012Validator(load_audit_schema())
    issues: list[ValidationIssue] = []
    for error in sorted(
        validator.iter_errors(data), key=lambda item: list(item.absolute_path)
    ):
        issues.append(
            ValidationIssue(
                code=f"schema.{error.validator}",
                path=_pointer(error.absolute_path),
                message=error.message,
            )
        )
    return issues


def _issue(
    issues: list[ValidationIssue],
    code: str,
    path: str,
    message: str,
    *related_ids: str,
) -> None:
    issues.append(ValidationIssue(code, path, message, tuple(related_ids)))


def _claims_for(entity: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    summary_audit = entity.get("summary_audit")
    if not isinstance(summary_audit, Mapping):
        return {}
    claims = summary_audit.get("claims")
    if not isinstance(claims, list):
        return {}
    return {
        str(claim["id"]): claim
        for claim in claims
        if isinstance(claim, Mapping) and isinstance(claim.get("id"), str)
    }


def _validate_summary(
    data: Mapping[str, Any],
    nodes: list[Mapping[str, Any]],
    issues: list[ValidationIssue],
) -> None:
    summary = data["summary"]
    findings = [node for node in nodes if node["type"] == "finding"]
    fixes = [node for node in nodes if node["type"] == "fix"]
    open_findings = [node for node in findings if node["status"] == "open"]
    done_fixes = [node for node in fixes if node["status"] == "done"]
    unscored = [
        node
        for node in open_findings
        if isinstance(node.get("extensions"), Mapping)
        and isinstance(node["extensions"].get("evidentloop"), Mapping)
        and (
            node["extensions"]["evidentloop"].get("downgraded_from") == "bug"
            or node["extensions"]["evidentloop"].get("unscored") is True
        )
    ]

    expected_counts = {
        "finding_count": len(findings),
        "open_finding_count": len(open_findings),
        "unscored_finding_count": len(unscored),
        "fix_count": len(fixes),
    }
    if "fix_done_count" in summary:
        expected_counts["fix_done_count"] = len(done_fixes)
    for field, expected in expected_counts.items():
        if summary[field] != expected:
            _issue(
                issues,
                "summary.count_mismatch",
                f"/summary/{field}",
                f"expected {expected}, got {summary[field]}",
            )

    status = summary["review_status"]
    verdict = summary["verdict"]
    score = summary["risk_score"]
    if status in {"not_reviewed", "partial", "failed"}:
        if verdict != "inconclusive":
            _issue(
                issues,
                "summary.invalid_verdict",
                "/summary/verdict",
                f"{status} review must be inconclusive",
            )
        if score is not None:
            _issue(
                issues,
                "summary.invalid_risk_score",
                "/summary/risk_score",
                f"{status} review must not have a numeric risk score",
            )
    elif verdict == "pass_candidate":
        if open_findings or score != 0:
            _issue(
                issues,
                "summary.invalid_pass_candidate",
                "/summary",
                "pass_candidate requires zero open findings and risk_score 0",
            )
    elif verdict == "concerns":
        if not open_findings or score is None:
            _issue(
                issues,
                "summary.invalid_concerns",
                "/summary",
                "concerns requires open findings and a numeric risk score",
            )
    elif verdict == "needs_human_triage":
        if (
            not open_findings
            or len(unscored) != len(open_findings)
            or score is not None
        ):
            _issue(
                issues,
                "summary.invalid_human_triage",
                "/summary",
                "needs_human_triage requires only unscored open findings and null score",
            )
    elif verdict == "inconclusive":
        if score is not None:
            _issue(
                issues,
                "summary.invalid_inconclusive_score",
                "/summary/risk_score",
                "inconclusive verdict must not have a numeric risk score",
            )


def _revision_event_state(
    finding: Mapping[str, Any],
) -> dict[str, Any]:
    model = finding["model_judgment"]
    return {
        "status": model["status"],
        "severity": model["severity"],
        "human": {},
    }


def _apply_revision_event(
    state: dict[str, Any], event: Mapping[str, Any], run_id: str
) -> None:
    action = event["action"]
    human = state["human"]
    human.pop("applied_run_id", None)
    if action == "accept":
        state["status"] = "open"
        human["disposition"] = "accept"
    elif action == "false_positive":
        state["status"] = "dismissed"
        human["disposition"] = "false_positive"
    elif action == "comment":
        if event.get("comment") is None:
            human.pop("comment", None)
        else:
            human["comment"] = event["comment"]
    elif action == "severity_override":
        severity = event.get("severity")
        if severity is None:
            state["severity"] = state["model_severity"]
            human.pop("severity_override", None)
        else:
            state["severity"] = severity
            human["severity_override"] = severity
    if human:
        human["applied_run_id"] = run_id
    else:
        human.clear()


def _validate_revisions(
    data: Mapping[str, Any],
    nodes: list[Mapping[str, Any]],
    edges: list[Mapping[str, Any]],
    issues: list[ValidationIssue],
) -> None:
    from .audit.feedback import FeedbackError, normalize_feedback
    from .audit.summary import build_summary

    runs = data["runs"]
    revision_runs = [
        (index, run)
        for index, run in enumerate(runs)
        if run.get("kind") == "feedback_revision"
    ]
    findings = {node["id"]: node for node in nodes if node["type"] == "finding"}
    states = {
        finding_id: _revision_event_state(finding)
        for finding_id, finding in findings.items()
    }
    for state in states.values():
        state["model_severity"] = state["severity"]

    if not revision_runs:
        summary = data["summary"]
        if summary.get("basis") != "model_review":
            _issue(
                issues,
                "revision.model_summary_basis",
                "/summary/basis",
                "a report without feedback revision runs must use model_review basis",
            )
        human_summary_fields = {
            "risk_delta",
            "model_verdict",
            "model_risk_score",
            "notice",
        }
        orphan_fields = sorted(human_summary_fields.intersection(summary))
        if orphan_fields:
            _issue(
                issues,
                "revision.orphan_human_summary",
                "/summary",
                "human adjudication summary fields require a feedback revision run: "
                + ", ".join(orphan_fields),
            )
        for finding_id, finding in findings.items():
            if "human_adjudication" in finding:
                _issue(
                    issues,
                    "revision.orphan_human_adjudication",
                    "/nodes",
                    "human adjudication requires a feedback revision run",
                    str(finding_id),
                )
            model = finding["model_judgment"]
            if (
                finding["status"] != model["status"]
                or finding["severity"] != model["severity"]
            ):
                _issue(
                    issues,
                    "revision.model_judgment_mismatch",
                    "/nodes",
                    "model-only finding state must match model_judgment",
                    str(finding_id),
                )
        return
    first_revision_index = revision_runs[0][0]
    if any(
        run.get("kind") != "feedback_revision" for run in runs[first_revision_index:]
    ):
        _issue(
            issues,
            "revision.invalid_run_order",
            "/runs",
            "model review runs cannot follow feedback revision runs",
        )
    first_snapshot = revision_runs[0][1]["revision"]["source_summary"]
    expected_source_summary = first_snapshot
    empty_verdict = (
        "pass_candidate"
        if first_snapshot["review_status"] == "complete"
        and first_snapshot["verdict"] in {"pass_candidate", "concerns"}
        else "inconclusive"
    )
    fixes = [node for node in nodes if node["type"] == "fix"]
    prior_effective = {
        finding_id: (state["status"], state["severity"])
        for finding_id, state in states.items()
    }
    for index, run in revision_runs:
        revision = run["revision"]
        try:
            normalized_events, normalized_hash = normalize_feedback(revision["events"])
        except FeedbackError as exc:
            _issue(
                issues,
                "revision.invalid_events",
                f"/runs/{index}/revision/events",
                str(exc),
                str(run["id"]),
            )
            normalized_events = []
            normalized_hash = None
        if normalized_events != revision["events"]:
            _issue(
                issues,
                "revision.events_not_normalized",
                f"/runs/{index}/revision/events",
                "revision events must be deduplicated and in canonical order",
                str(run["id"]),
            )
        if normalized_hash != revision["feedback_sha256"]:
            _issue(
                issues,
                "revision.feedback_hash_mismatch",
                f"/runs/{index}/revision/feedback_sha256",
                "feedback_sha256 does not match the normalized adopted events",
                str(run["id"]),
            )
        expected_source_run = runs[index - 1]["id"] if index else None
        if index == 0 or revision["source_run_id"] != expected_source_run:
            _issue(
                issues,
                "revision.source_run_mismatch",
                f"/runs/{index}/revision/source_run_id",
                "feedback revision must reference the immediately preceding run",
                str(run["id"]),
            )
        matching_edges = [
            edge
            for edge in edges
            if edge["type"] == "supersedes_run"
            and edge["from"] == run["id"]
            and edge["to"] == revision["source_run_id"]
        ]
        if len(matching_edges) != 1:
            _issue(
                issues,
                "revision.lineage_mismatch",
                f"/runs/{index}/revision",
                "feedback revision requires exactly one supersedes_run edge",
                str(run["id"]),
            )
        if revision["source_summary"] != expected_source_summary:
            _issue(
                issues,
                "revision.source_summary_mismatch",
                f"/runs/{index}/revision/source_summary",
                "source_summary does not match the preceding revision state",
                str(run["id"]),
            )
        for event in revision["events"]:
            target_id = event["target_id"]
            finding = findings.get(target_id)
            if finding is None:
                _issue(
                    issues,
                    "revision.unknown_finding",
                    f"/runs/{index}/revision/events",
                    "feedback target does not exist",
                    str(target_id),
                )
                continue
            if (
                event["graph_id"] != data["graph_id"]
                or event["run_id"] != revision["source_run_id"]
                or event["fingerprint"] != finding["fingerprint"]
                or event["source_audit_sha256"] != revision["source_audit_sha256"]
            ):
                _issue(
                    issues,
                    "revision.event_identity_mismatch",
                    f"/runs/{index}/revision/events",
                    "feedback event identity does not match its revision source",
                    str(target_id),
                )
                continue
            _apply_revision_event(states[target_id], event, str(run["id"]))

        projected = []
        for finding_id, finding in findings.items():
            item = dict(finding)
            item["status"] = states[finding_id]["status"]
            item["severity"] = states[finding_id]["severity"]
            projected.append(item)
        current_effective = {
            finding_id: (state["status"], state["severity"])
            for finding_id, state in states.items()
        }
        if prior_effective == current_effective:
            calculated = {
                field: expected_source_summary[field]
                for field in (
                    "review_status",
                    "verdict",
                    "risk_score",
                    "finding_count",
                    "unscored_finding_count",
                    "open_finding_count",
                    "fix_count",
                    "fix_done_count",
                )
                if field in expected_source_summary
            }
        else:
            calculated = build_summary(
                projected,
                fixes,
                review_status=first_snapshot["review_status"],
                empty_verdict=empty_verdict,
            )
        calculated["summary_audit_status"] = first_snapshot.get(
            "summary_audit_status", "not_audited"
        )
        calculated["risk_delta"] = (
            calculated["risk_score"] - expected_source_summary["risk_score"]
            if calculated["risk_score"] is not None
            and expected_source_summary["risk_score"] is not None
            else None
        )
        calculated.update(
            {
                "basis": "human_adjudication",
                "model_verdict": first_snapshot["verdict"],
                "model_risk_score": first_snapshot["risk_score"],
                "notice": "基于人工裁定，未重新审查代码",
            }
        )
        if "extensions" in first_snapshot:
            calculated["extensions"] = first_snapshot["extensions"]
        expected_source_summary = calculated
        prior_effective = current_effective
        if run["status"] != calculated["verdict"]:
            _issue(
                issues,
                "revision.run_verdict_mismatch",
                f"/runs/{index}/status",
                "revision run status does not match replayed feedback",
                str(run["id"]),
            )

    for finding_id, finding in findings.items():
        state = states[finding_id]
        expected_human = state["human"] or None
        if (
            finding["status"] != state["status"]
            or finding["severity"] != state["severity"]
            or finding.get("human_adjudication") != expected_human
        ):
            _issue(
                issues,
                "revision.finding_state_mismatch",
                "/nodes",
                "finding state does not match replayed feedback",
                str(finding_id),
            )
    comparable = {key: data["summary"].get(key) for key in expected_source_summary}
    if comparable != expected_source_summary:
        _issue(
            issues,
            "revision.summary_mismatch",
            "/summary",
            "summary does not match replayed feedback",
        )


def _validate_finding_anchor(
    node: Mapping[str, Any],
    index: int,
    issues: list[ValidationIssue],
) -> None:
    hunk_fields = {
        "hunk_id",
        "start_line",
        "end_line",
        "line_side",
        "highlight_lines",
        "hunk",
    }
    exact_fields = {"file_path", *hunk_fields}
    present_hunk_fields = hunk_fields.intersection(node)
    if node["category"] == "bug" and not exact_fields.issubset(node):
        missing = ", ".join(sorted(exact_fields - set(node)))
        _issue(
            issues,
            "anchor.bug_requires_exact",
            f"/nodes/{index}",
            f"bug finding is missing exact anchor fields: {missing}",
            str(node["id"]),
        )
        return
    if present_hunk_fields and (
        present_hunk_fields != hunk_fields or "file_path" not in node
    ):
        missing = ", ".join(sorted(exact_fields - set(node)))
        _issue(
            issues,
            "anchor.incomplete",
            f"/nodes/{index}",
            f"partial hunk anchor is not allowed; missing: {missing}",
            str(node["id"]),
        )
        return
    if not present_hunk_fields:
        return

    if node["start_line"] > node["end_line"]:
        _issue(
            issues,
            "anchor.invalid_range",
            f"/nodes/{index}/start_line",
            "start_line must be less than or equal to end_line",
            str(node["id"]),
        )
    try:
        hunk = parse_hunk(str(node["hunk"]))
    except HunkParseError as exc:
        _issue(
            issues,
            "anchor.invalid_hunk",
            f"/nodes/{index}/hunk",
            str(exc),
            str(node["id"]),
        )
        return

    side = str(node["line_side"])
    available = hunk.line_numbers(side)
    expected_range = set(range(int(node["start_line"]), int(node["end_line"]) + 1))
    if not expected_range.issubset(available):
        _issue(
            issues,
            "anchor.range_outside_hunk",
            f"/nodes/{index}/start_line",
            f"{side} line range is not fully present in the hunk",
            str(node["id"]),
        )
    highlights = set(node["highlight_lines"])
    if (
        not highlights
        or not highlights.issubset(expected_range)
        or not highlights.issubset(available)
    ):
        _issue(
            issues,
            "anchor.invalid_highlight",
            f"/nodes/{index}/highlight_lines",
            "highlight lines must be non-empty and contained in the trusted range",
            str(node["id"]),
        )


def validate_semantics(data: Mapping[str, Any]) -> list[ValidationIssue]:
    """Validate global IDs, relations, claims, anchors, and summary semantics."""
    issues: list[ValidationIssue] = []
    runs = [run for run in data["runs"] if isinstance(run, Mapping)]
    nodes = [node for node in data["nodes"] if isinstance(node, Mapping)]
    edges = [edge for edge in data["edges"] if isinstance(edge, Mapping)]
    entities: dict[str, Mapping[str, Any]] = {}
    entity_types: dict[str, str] = {}
    all_ids: dict[str, str] = {}

    for kind, records in (("run", runs), ("node", nodes), ("edge", edges)):
        for index, record in enumerate(records):
            identifier = str(record["id"])
            path = f"/{'runs' if kind == 'run' else kind + 's'}/{index}/id"
            if identifier in all_ids:
                _issue(
                    issues,
                    "id.duplicate",
                    path,
                    f"ID already used by {all_ids[identifier]}",
                    identifier,
                )
            else:
                all_ids[identifier] = path
            if kind != "edge":
                entities[identifier] = record
                entity_types[identifier] = (
                    "run" if kind == "run" else str(record["type"])
                )

    claim_owners: dict[str, str] = {}
    for collection, records in (("runs", runs), ("nodes", nodes)):
        for index, record in enumerate(records):
            for claim_id in _claims_for(record):
                path = f"/{collection}/{index}/summary_audit/claims"
                if claim_id in claim_owners:
                    _issue(
                        issues,
                        "claim.duplicate",
                        path,
                        f"claim ID already belongs to {claim_owners[claim_id]}",
                        claim_id,
                    )
                else:
                    claim_owners[claim_id] = str(record["id"])

    contracts: dict[str, set[tuple[str, str]]] = {
        "contains_change": {("run", "change")},
        "supersedes_run": {("run", "run")},
        "changes_file": {("change", "file")},
        "finding_in_file": {("finding", "file")},
        "supported_by_evidence": {("finding", "evidence")},
        "requires_fix": {("finding", "fix")},
        "supports_claim": {
            ("finding", "run"),
            ("finding", "change"),
            ("evidence", "run"),
            ("evidence", "change"),
        },
        "challenges_claim": {
            ("finding", "run"),
            ("finding", "change"),
            ("evidence", "run"),
            ("evidence", "change"),
        },
    }

    finding_file_edges: dict[str, str] = {}
    for index, edge in enumerate(edges):
        source_id = str(edge["from"])
        target_id = str(edge["to"])
        edge_id = str(edge["id"])
        path = f"/edges/{index}"
        if source_id not in entities:
            _issue(
                issues,
                "edge.unknown_from",
                f"{path}/from",
                "edge source does not exist",
                edge_id,
                source_id,
            )
        if target_id not in entities:
            _issue(
                issues,
                "edge.unknown_to",
                f"{path}/to",
                "edge target does not exist",
                edge_id,
                target_id,
            )
        if source_id not in entities or target_id not in entities:
            continue

        edge_type = str(edge["type"])
        pair = (entity_types[source_id], entity_types[target_id])
        if edge_type == "rendered_as":
            allowed = pair[1] == "artifact" and pair[0] != "artifact"
        else:
            allowed = pair in contracts.get(edge_type, set())
        if not allowed:
            _issue(
                issues,
                "edge.invalid_endpoint_types",
                f"{path}/type",
                f"{edge_type} does not allow {pair[0]} -> {pair[1]}",
                edge_id,
                source_id,
                target_id,
            )

        is_claim_edge = edge_type in {"supports_claim", "challenges_claim"}
        claim_id = edge.get("claim_id")
        if is_claim_edge:
            if not isinstance(claim_id, str):
                _issue(
                    issues,
                    "claim.missing_reference",
                    f"{path}/claim_id",
                    "claim edge requires claim_id",
                    edge_id,
                )
            elif claim_id not in _claims_for(entities[target_id]):
                _issue(
                    issues,
                    "claim.unknown_reference",
                    f"{path}/claim_id",
                    "claim_id does not belong to the edge target",
                    edge_id,
                    claim_id,
                    target_id,
                )
        elif claim_id is not None:
            _issue(
                issues,
                "claim.unexpected_reference",
                f"{path}/claim_id",
                "claim_id is only valid on claim edges",
                edge_id,
            )

        if edge_type == "finding_in_file":
            finding_file_edges[source_id] = target_id

    file_paths = {
        str(node["id"]): str(node["path"]) for node in nodes if node["type"] == "file"
    }
    fingerprints: dict[str, str] = {}
    for index, node in enumerate(nodes):
        if node["type"] != "finding":
            continue
        finding_id = str(node["id"])
        fingerprint = str(node["fingerprint"])
        if fingerprint in fingerprints:
            _issue(
                issues,
                "finding.duplicate_fingerprint",
                f"/nodes/{index}/fingerprint",
                "fingerprint must be unique within the graph",
                finding_id,
                fingerprints[fingerprint],
            )
        else:
            fingerprints[fingerprint] = finding_id

        _validate_finding_anchor(node, index, issues)
        file_path = node.get("file_path")
        edge_target = finding_file_edges.get(finding_id)
        if isinstance(file_path, str):
            if edge_target is None:
                _issue(
                    issues,
                    "finding.missing_file_edge",
                    f"/nodes/{index}/file_path",
                    "trusted file_path requires a finding_in_file edge",
                    finding_id,
                )
            elif file_paths.get(edge_target) != file_path:
                _issue(
                    issues,
                    "finding.file_edge_mismatch",
                    f"/nodes/{index}/file_path",
                    "file_path does not match the linked file node",
                    finding_id,
                    edge_target,
                )
        elif edge_target is not None:
            _issue(
                issues,
                "finding.unexpected_file_edge",
                f"/nodes/{index}",
                "finding without file_path cannot have finding_in_file edge",
                finding_id,
                edge_target,
            )

    _validate_summary(data, nodes, issues)
    _validate_revisions(data, nodes, edges, issues)
    if runs and runs[-1]["status"] != data["summary"]["verdict"]:
        _issue(
            issues,
            "run.verdict_mismatch",
            f"/runs/{len(runs) - 1}/status",
            "latest run status must equal summary verdict",
            str(runs[-1]["id"]),
        )
    return issues


def validate_audit(data: Any) -> list[ValidationIssue]:
    """Validate structure first, then cross-object semantics."""
    structural = validate_structure(data)
    if structural:
        return structural
    return validate_semantics(data)


def assert_valid_audit(data: Any) -> None:
    """Raise :class:`AuditValidationError` for any invalid audit document."""
    issues = validate_audit(data)
    if issues:
        raise AuditValidationError(issues)
