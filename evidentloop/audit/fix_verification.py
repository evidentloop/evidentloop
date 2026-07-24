"""Typed fix-verification request and its strict source pre-validation.

The failure order is part of the public contract: the expected/actual source
report version is byte-checked before schema and semantic validation, then
diff_version and per-target identity/open checks, and only then is the current
diff read and frozen. Every failure happens before any output-directory or
staging side effect, and the source report is never modified.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from evidentloop.validation import (
    SCHEMA_VERSION,
    AuditValidationError,
    assert_valid_audit,
    fix_verification_context_problems,
)
from evidentloop.versions import audit_diff_version, content_version, is_content_version

from .finalize import AuditWorkflowError, _prepare_local_diff


@dataclass(frozen=True)
class FixVerificationTarget:
    """One explicitly selected source finding plus the user's fix claim."""

    finding_id: str
    fingerprint: str
    claim: str


@dataclass(frozen=True)
class FixVerificationRequest:
    """User request to verify fixes in the current diff against one source report."""

    source_audit_json: str | Path
    expected_source_report_version: str
    targets: tuple[FixVerificationTarget, ...]


def validate_fix_verification_source(
    request: FixVerificationRequest,
) -> dict[str, Any]:
    """Validate the source report and freeze the fix-verification context.

    Returns the one-hop context (direct predecessor versions plus per-target
    frozen identity, title and claim); absolute paths are deliberately absent.
    """
    if not request.targets:
        raise AuditWorkflowError(
            "fix verification requires at least one target finding"
        )
    seen: set[str] = set()
    for target in request.targets:
        if not target.finding_id or not target.fingerprint:
            raise AuditWorkflowError(
                "every fix verification target requires finding_id and fingerprint"
            )
        if not is_content_version(target.fingerprint):
            raise AuditWorkflowError(
                f"fix verification target {target.finding_id} has an invalid fingerprint"
            )
        if not target.claim.strip():
            raise AuditWorkflowError(
                f"fix verification target {target.finding_id} requires a non-empty claim"
            )
        if target.finding_id in seen:
            raise AuditWorkflowError(
                f"duplicate fix verification target: {target.finding_id}"
            )
        seen.add(target.finding_id)
    if not is_content_version(request.expected_source_report_version):
        raise AuditWorkflowError(
            "expected_source_report_version must use sha256:<64 lowercase hex>"
        )

    try:
        raw = Path(request.source_audit_json).read_bytes()
    except OSError as exc:
        raise AuditWorkflowError(f"cannot read source audit: {exc}") from exc
    actual_version = content_version(raw)
    if actual_version != request.expected_source_report_version:
        raise AuditWorkflowError(
            "source report version does not match the expected version; "
            "re-open the source report and select targets again"
        )
    try:
        audit = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditWorkflowError(f"source audit is not valid JSON: {exc}") from exc
    if not isinstance(audit, dict) or audit.get("schema_version") != SCHEMA_VERSION:
        raise AuditWorkflowError(
            f"fix verification accepts only audit schema {SCHEMA_VERSION} sources; "
            "regenerate the source report with the current runtime"
        )
    try:
        assert_valid_audit(audit)
    except AuditValidationError as exc:
        raise AuditWorkflowError(f"source audit failed validation: {exc}") from exc
    source_diff_version = audit_diff_version(audit)
    if not source_diff_version:
        raise AuditWorkflowError(
            "source audit has no diff_version and cannot anchor fix verification"
        )

    findings = {
        node["id"]: node for node in audit["nodes"] if node["type"] == "finding"
    }
    frozen_targets: list[dict[str, str]] = []
    for index, target in enumerate(request.targets, start=1):
        finding = findings.get(target.finding_id)
        if finding is None:
            raise AuditWorkflowError(
                f"unknown fix verification target: {target.finding_id}"
            )
        if finding["fingerprint"] != target.fingerprint:
            raise AuditWorkflowError(
                f"fingerprint of {target.finding_id} does not match the current "
                "source report; re-select targets from that report"
            )
        if finding["status"] != "open":
            raise AuditWorkflowError(
                f"{target.finding_id} is not open in the source report; "
                "adjudicate it there before requesting fix verification"
            )
        frozen_targets.append(
            {
                "claim_id": f"claim-{index:03d}",
                "finding_id": target.finding_id,
                "fingerprint": target.fingerprint,
                "source_title": finding["title"],
                "claim": target.claim.strip(),
            }
        )
    context = {
        "version": 1,
        "source_report_version": actual_version,
        "source_diff_version": source_diff_version,
        "targets": frozen_targets,
    }
    problems = fix_verification_context_problems(context)
    if problems:
        raise AuditWorkflowError(
            "invalid frozen fix verification context: " + "; ".join(problems)
        )
    return context


def prepare_fix_verification(
    repo_path: str | Path,
    diff_spec: str,
    request: FixVerificationRequest,
    output_dir: str | Path | None = None,
    *,
    focus: str | None = None,
) -> dict[str, str]:
    """Prepare a host review whose current diff verifies explicit source findings."""
    context = validate_fix_verification_source(request)
    return _prepare_local_diff(
        repo_path,
        diff_spec,
        output_dir,
        focus=focus,
        fix_verification=context,
    )


_REQUEST_KEYS = {"source_audit_json", "expected_source_report_version", "targets"}
_TARGET_KEYS = {"finding_id", "fingerprint", "claim"}


def fix_verification_request_from_dict(value: object) -> FixVerificationRequest:
    """Parse a strict fix-verification request document into the typed request."""
    if not isinstance(value, dict):
        raise AuditWorkflowError("fix verification request must be a JSON object")
    unknown = set(value) - _REQUEST_KEYS
    if unknown:
        raise AuditWorkflowError(
            "fix verification request has unknown fields: " + ", ".join(sorted(unknown))
        )
    missing = _REQUEST_KEYS - set(value)
    if missing:
        raise AuditWorkflowError(
            "fix verification request is missing fields: " + ", ".join(sorted(missing))
        )
    source = value["source_audit_json"]
    version = value["expected_source_report_version"]
    raw_targets = value["targets"]
    if not isinstance(source, str) or not source.strip():
        raise AuditWorkflowError("source_audit_json must be a non-empty string")
    if not isinstance(version, str) or not is_content_version(version):
        raise AuditWorkflowError(
            "expected_source_report_version must use sha256:<64 lowercase hex>"
        )
    if not isinstance(raw_targets, list) or not raw_targets:
        raise AuditWorkflowError("targets must be a non-empty list")
    targets: list[FixVerificationTarget] = []
    for index, raw in enumerate(raw_targets, start=1):
        if not isinstance(raw, dict):
            raise AuditWorkflowError(f"target {index} must be an object")
        unknown_target = set(raw) - _TARGET_KEYS
        if unknown_target:
            raise AuditWorkflowError(
                f"target {index} has unknown fields: "
                + ", ".join(sorted(unknown_target))
            )
        missing_target = _TARGET_KEYS - set(raw)
        if missing_target:
            raise AuditWorkflowError(
                f"target {index} is missing fields: "
                + ", ".join(sorted(missing_target))
            )
        for key in sorted(_TARGET_KEYS):
            if not isinstance(raw[key], str) or not raw[key].strip():
                raise AuditWorkflowError(
                    f"target {index} field {key} must be a non-empty string"
                )
        if not is_content_version(raw["fingerprint"]):
            raise AuditWorkflowError(
                f"target {index} fingerprint must use sha256:<64 lowercase hex>"
            )
        targets.append(
            FixVerificationTarget(
                finding_id=raw["finding_id"],
                fingerprint=raw["fingerprint"],
                claim=raw["claim"],
            )
        )
    return FixVerificationRequest(
        source_audit_json=source,
        expected_source_report_version=version,
        targets=tuple(targets),
    )
