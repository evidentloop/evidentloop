"""Fix-verification source pre-validation, failure order, and focus contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evidentloop.adapters.gitdiff import collect_git_diff
from evidentloop.audit.finalize import AuditWorkflowError, prepare_local_diff
from evidentloop.audit.fix_verification import (
    FixVerificationRequest,
    FixVerificationTarget,
    prepare_fix_verification,
    validate_fix_verification_source,
)
from evidentloop.review.schema import compute_fingerprint
from evidentloop.versions import content_version, diff_version_from_fingerprint
from tests.audit_helpers import demo_audit
from tests.git_helpers import initialized_repo, stage_simple_change


OLD_DIFF_VERSION = "sha256:" + "a" * 64


def _write_source(
    path: Path,
    *,
    diff_version: str | None = OLD_DIFF_VERSION,
    mutate=None,
) -> tuple[str, dict]:
    audit = demo_audit()
    if diff_version is not None:
        audit.setdefault("extensions", {}).setdefault("evidentloop", {})[
            "diff_version"
        ] = diff_version
    if mutate is not None:
        mutate(audit)
    raw = (json.dumps(audit, ensure_ascii=False, indent=2) + "\n").encode()
    path.write_bytes(raw)
    return content_version(raw), audit


def _target(
    audit: dict, finding_id: str, claim: str = "该问题已修复"
) -> FixVerificationTarget:
    finding = next(node for node in audit["nodes"] if node.get("id") == finding_id)
    return FixVerificationTarget(
        finding_id=finding_id,
        fingerprint=finding["fingerprint"],
        claim=claim,
    )


def _request(
    source: Path,
    version: str,
    targets: tuple[FixVerificationTarget, ...],
) -> FixVerificationRequest:
    return FixVerificationRequest(
        source_audit_json=source,
        expected_source_report_version=version,
        targets=targets,
    )


def test_prepare_freezes_one_hop_context_without_absolute_paths(tmp_path: Path) -> None:
    repo = initialized_repo(tmp_path)
    stage_simple_change(repo)
    source = tmp_path / "source-audit.json"
    version, audit = _write_source(source)
    request = _request(
        source,
        version,
        (_target(audit, "finding-001", "  缓存路径已改为先失效再写入  "),),
    )

    locator = prepare_fix_verification(repo, "staged", request, repo / "reports" / "fv")

    skeleton = json.loads(
        (Path(locator["staging_dir"]) / ".run" / "audit-skeleton.json").read_text(
            encoding="utf-8"
        )
    )
    context = skeleton["fix_verification"]
    assert context["version"] == 1
    assert context["source_report_version"] == version
    assert context["source_diff_version"] == OLD_DIFF_VERSION
    assert context["targets"] == [
        {
            "claim_id": "claim-001",
            "finding_id": "finding-001",
            "fingerprint": audit["nodes"][3]["fingerprint"],
            "source_title": "旧 token 仍可能被缓存层返回",
            "claim": "缓存路径已改为先失效再写入",
        }
    ]
    assert str(tmp_path) not in json.dumps(context, ensure_ascii=False)


def test_request_shape_is_validated_before_reading_the_source(tmp_path: Path) -> None:
    audit = demo_audit()
    missing = tmp_path / "does-not-exist.json"
    valid_target = _target(audit, "finding-001")

    cases = [
        ((), "sha256:" + "b" * 64, "at least one target"),
        (
            (FixVerificationTarget("finding-001", valid_target.fingerprint, "  "),),
            "sha256:" + "b" * 64,
            "non-empty claim",
        ),
        (
            (FixVerificationTarget("", valid_target.fingerprint, "已修复"),),
            "sha256:" + "b" * 64,
            "finding_id and fingerprint",
        ),
        ((valid_target, valid_target), "sha256:" + "b" * 64, "duplicate"),
        ((valid_target,), "", "expected_source_report_version"),
        ((valid_target,), "not-a-version", "expected_source_report_version"),
        (
            (FixVerificationTarget("finding-001", "not-a-fingerprint", "已修复"),),
            "sha256:" + "b" * 64,
            "invalid fingerprint",
        ),
    ]
    for targets, version, match in cases:
        with pytest.raises(AuditWorkflowError, match=match):
            validate_fix_verification_source(_request(missing, version, targets))


def test_source_byte_version_is_checked_before_parsing(tmp_path: Path) -> None:
    audit = demo_audit()
    garbage = tmp_path / "garbage.json"
    garbage.write_bytes(b"{not json")
    target = _target(audit, "finding-001")

    with pytest.raises(AuditWorkflowError, match="does not match the expected version"):
        validate_fix_verification_source(
            _request(garbage, "sha256:" + "c" * 64, (target,))
        )

    with pytest.raises(AuditWorkflowError, match="not valid JSON"):
        validate_fix_verification_source(
            _request(garbage, content_version(garbage.read_bytes()), (target,))
        )


def test_source_schema_gate_precedes_semantic_validation(tmp_path: Path) -> None:
    source = tmp_path / "old-schema.json"

    def _break(audit: dict) -> None:
        audit["schema_version"] = "0.4"
        audit["summary"]["finding_count"] = 99

    version, audit = _write_source(source, mutate=_break)

    with pytest.raises(AuditWorkflowError, match="schema 0.5"):
        validate_fix_verification_source(
            _request(source, version, (_target(audit, "finding-001"),))
        )


def test_source_without_diff_version_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "no-diff-version.json"
    version, audit = _write_source(source, diff_version=None)

    with pytest.raises(AuditWorkflowError, match="no diff_version"):
        validate_fix_verification_source(
            _request(source, version, (_target(audit, "finding-001"),))
        )


def test_target_identity_and_status_gates(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    version, audit = _write_source(source)

    with pytest.raises(AuditWorkflowError, match="unknown fix verification target"):
        validate_fix_verification_source(
            _request(
                source,
                version,
                (FixVerificationTarget("finding-999", "sha256:" + "d" * 64, "已修复"),),
            )
        )

    with pytest.raises(AuditWorkflowError, match="fingerprint of finding-001"):
        validate_fix_verification_source(
            _request(
                source,
                version,
                (FixVerificationTarget("finding-001", "sha256:" + "d" * 64, "已修复"),),
            )
        )

    fixed = tmp_path / "fixed.json"

    def _close_second(audit: dict) -> None:
        finding = next(
            node for node in audit["nodes"] if node.get("id") == "finding-002"
        )
        finding["status"] = "fixed"
        finding["model_judgment"]["status"] = "fixed"
        audit["summary"]["open_finding_count"] = 1

    fixed_version, fixed_audit = _write_source(fixed, mutate=_close_second)
    with pytest.raises(AuditWorkflowError, match="not open"):
        validate_fix_verification_source(
            _request(fixed, fixed_version, (_target(fixed_audit, "finding-002"),))
        )


def test_same_diff_is_rejected_before_any_staging_side_effect(tmp_path: Path) -> None:
    repo = initialized_repo(tmp_path)
    stage_simple_change(repo)
    current_diff_version = diff_version_from_fingerprint(
        compute_fingerprint(collect_git_diff(repo, "staged").diff)
    )
    source = tmp_path / "same-diff.json"
    version, audit = _write_source(source, diff_version=current_diff_version)

    with pytest.raises(AuditWorkflowError, match="requires a new diff") as error:
        prepare_fix_verification(
            repo,
            "staged",
            _request(source, version, (_target(audit, "finding-001"),)),
            repo / "reports" / "same",
        )

    assert error.value.staging_dir is None
    assert not (repo / "reports").exists()


def test_prepare_focus_three_states(tmp_path: Path) -> None:
    repo = initialized_repo(tmp_path)
    stage_simple_change(repo)

    default = prepare_local_diff(repo, "staged", repo / "reports" / "no-focus")
    default_pack = json.loads(
        (Path(default["staging_dir"]) / ".run" / "review-pack.json").read_text(
            encoding="utf-8"
        )
    )
    assert default_pack["focus"] is None
    default_prompt = (Path(default["staging_dir"]) / ".run" / "prompt.md").read_text(
        encoding="utf-8"
    )
    assert "(no focus specified)" in default_prompt

    focused = prepare_local_diff(
        repo, "staged", repo / "reports" / "focused", focus="缓存一致性"
    )
    focused_pack = json.loads(
        (Path(focused["staging_dir"]) / ".run" / "review-pack.json").read_text(
            encoding="utf-8"
        )
    )
    assert focused_pack["focus"] == ["缓存一致性"]
    focused_prompt = (Path(focused["staging_dir"]) / ".run" / "prompt.md").read_text(
        encoding="utf-8"
    )
    assert "缓存一致性" in focused_prompt

    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    with pytest.raises(AuditWorkflowError, match="focus must be non-empty"):
        prepare_local_diff(not_a_repo, "staged", not_a_repo / "out", focus="   ")
