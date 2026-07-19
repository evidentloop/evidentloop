"""JSON Schema and semantic audit validation tests."""

from __future__ import annotations

import copy

import pytest

from evidentloop.validation import (
    AuditValidationError,
    assert_valid_audit,
    load_audit_schema,
    validate_audit,
    validate_structure,
)
from tests.audit_helpers import demo_audit, minimal_audit


def test_schema_declares_2020_12_and_validates_reference_demo() -> None:
    schema = load_audit_schema()
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert validate_audit(demo_audit()) == []


def test_strict_core_allows_namespaced_extensions() -> None:
    audit = minimal_audit()
    audit["extensions"] = {"evidentloop": {"test": True}}
    audit["nodes"][0]["extensions"] = {"vendor.profile": {"value": 1}}
    assert validate_audit(audit) == []


def test_diff_version_uses_content_version_format() -> None:
    audit = minimal_audit()
    audit["extensions"] = {"evidentloop": {"diff_version": "not-a-version"}}

    issues = validate_audit(audit)

    assert any(issue.code == "version.invalid_diff_version" for issue in issues)


def test_historical_schema_version_is_rejected_by_current_runtime() -> None:
    audit = minimal_audit()
    audit["schema_version"] = "0.3"

    issues = validate_structure(audit)

    assert any(
        issue.code == "schema.const" and issue.path == "/schema_version"
        for issue in issues
    )


def test_strict_core_rejects_unknown_fields_and_bad_extension_names() -> None:
    audit = minimal_audit()
    audit["unexpected"] = True
    issues = validate_structure(audit)
    assert issues[0].code == "schema.additionalProperties"
    assert issues[0].path == "/"

    audit = minimal_audit()
    audit["extensions"] = {"Bad Namespace": {}}
    issues = validate_structure(audit)
    assert any(issue.code == "schema.pattern" for issue in issues)


def test_artifact_node_and_rendered_as_edge_are_supported() -> None:
    audit = minimal_audit()
    audit["nodes"].append(
        {
            "id": "artifact-html",
            "type": "artifact",
            "kind": "audit_html",
            "path": "audit.html",
            "media_type": "text/html",
        }
    )
    audit["edges"].append(
        {
            "id": "edge-rendered",
            "type": "rendered_as",
            "from": "run-minimal",
            "to": "artifact-html",
        }
    )
    assert validate_audit(audit) == []


def test_duplicate_id_reports_json_path_and_related_id() -> None:
    audit = minimal_audit()
    audit["nodes"][1]["id"] = audit["nodes"][0]["id"]
    issues = validate_audit(audit)
    duplicate = next(issue for issue in issues if issue.code == "id.duplicate")
    assert duplicate.path == "/nodes/1/id"
    assert duplicate.related_ids == ("change-minimal",)


def test_edge_endpoint_and_claim_reference_errors_are_precise() -> None:
    audit = demo_audit()
    audit["edges"][0]["to"] = "missing-change"
    audit["edges"][-1]["claim_id"] = "claim-missing"
    issues = validate_audit(audit)
    assert any(
        issue.code == "edge.unknown_to"
        and issue.path == "/edges/0/to"
        and "missing-change" in issue.related_ids
        for issue in issues
    )
    assert any(
        issue.code == "claim.unknown_reference"
        and issue.path == "/edges/9/claim_id"
        and "claim-missing" in issue.related_ids
        for issue in issues
    )


def test_edge_endpoint_type_contract_is_enforced() -> None:
    audit = minimal_audit()
    audit["edges"][1]["from"] = "run-minimal"
    issues = validate_audit(audit)
    assert any(issue.code == "edge.invalid_endpoint_types" for issue in issues)


def test_bug_requires_complete_trusted_anchor() -> None:
    audit = demo_audit()
    del audit["nodes"][3]["hunk"]
    issues = validate_audit(audit)
    assert any(
        issue.code == "anchor.bug_requires_exact"
        and issue.related_ids == ("finding-001",)
        for issue in issues
    )


def test_hunk_range_and_highlight_must_resolve() -> None:
    audit = demo_audit()
    audit["nodes"][3]["highlight_lines"] = [999]
    issues = validate_audit(audit)
    assert any(issue.code == "anchor.invalid_highlight" for issue in issues)


def test_complete_review_can_remain_inconclusive_when_input_is_insufficient() -> None:
    audit = minimal_audit(
        review_status="complete",
        verdict="inconclusive",
        risk_score=None,
    )
    assert_valid_audit(audit)

    audit["summary"]["risk_score"] = 0
    issues = validate_audit(audit)
    assert any(issue.code == "summary.invalid_inconclusive_score" for issue in issues)


def test_summary_counts_and_status_combinations_are_cross_checked() -> None:
    audit = minimal_audit()
    audit["summary"]["finding_count"] = 3
    audit["summary"]["risk_score"] = None
    issues = validate_audit(audit)
    codes = {issue.code for issue in issues}
    assert "summary.count_mismatch" in codes
    assert "summary.invalid_pass_candidate" in codes


def test_validation_error_preserves_structured_issues() -> None:
    audit = minimal_audit(review_status="partial", verdict="concerns", risk_score=10)
    with pytest.raises(AuditValidationError) as captured:
        assert_valid_audit(audit)
    assert captured.value.issues
    assert all(issue.path.startswith("/") for issue in captured.value.issues)


def test_schema_does_not_mutate_input() -> None:
    audit = demo_audit()
    before = copy.deepcopy(audit)
    assert_valid_audit(audit)
    assert audit == before
