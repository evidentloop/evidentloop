"""End-to-end fix verification flow: prompt, gate, claims, provenance, CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evidentloop.audit.finalize import finalize_review
from evidentloop.audit.fix_verification import (
    FixVerificationRequest,
    FixVerificationTarget,
    fix_verification_request_from_dict,
    prepare_fix_verification,
)
from evidentloop.cli import main
from evidentloop.review.claims import (
    aggregate_claim_status,
    parse_fix_verification_results,
)
from evidentloop.validation import validate_audit
from evidentloop.versions import content_version
from tests.audit_helpers import demo_audit
from tests.git_helpers import initialized_repo, stage_simple_change


OLD_DIFF_VERSION = "sha256:" + "a" * 64


def _write_source(path: Path) -> tuple[str, dict]:
    audit = demo_audit()
    audit.setdefault("extensions", {}).setdefault("evidentloop", {})["diff_version"] = (
        OLD_DIFF_VERSION
    )
    raw = (json.dumps(audit, ensure_ascii=False, indent=2) + "\n").encode()
    path.write_bytes(raw)
    return content_version(raw), audit


def _target(audit: dict, finding_id: str, claim: str) -> FixVerificationTarget:
    finding = next(node for node in audit["nodes"] if node.get("id") == finding_id)
    return FixVerificationTarget(
        finding_id=finding_id, fingerprint=finding["fingerprint"], claim=claim
    )


def _prepare_flow(
    tmp_path: Path,
    targets: tuple[FixVerificationTarget, ...],
) -> tuple[dict[str, str], bytes]:
    repo = initialized_repo(tmp_path)
    stage_simple_change(repo)
    source = tmp_path / "source-audit.json"
    version, audit = _write_source(source)
    request = FixVerificationRequest(
        source_audit_json=source,
        expected_source_report_version=version,
        targets=targets,
    )
    source_bytes = source.read_bytes()
    locator = prepare_fix_verification(repo, "staged", request, repo / "reports" / "fv")
    return locator, source_bytes


def _header(locator: dict[str, str]) -> str:
    run_dir = Path(locator["staging_dir"]) / ".run"
    index = json.loads((run_dir / "hunk-index.json").read_text(encoding="utf-8"))
    return index["hunks"][0]["header"]


def _raw(
    locator: dict[str, str],
    *,
    findings: str = "No findings.",
    overall: str = "本次变更未发现新问题。",
    claims: str = "",
) -> str:
    return (
        f"<!-- evidentloop-run-id: {locator['run_id']} -->\n"
        "## Section 0: Change Summary\n\n"
        "- **Overview**: 本次改动验证旧问题并独立审查当前 diff。\n"
        "- **Review focus**: 核验修复声明与当前代码是否一致。\n\n"
        "### theme-001\n"
        "- **Title**: 验证旧问题修复\n"
        "- **Summary**: 当前 diff 针对显式选择的旧问题提供新证据。\n"
        "- **Impact**: 应用代码与修复验证链路\n\n"
        f"## Section 1: Findings\n\n{findings}\n\n"
        "## Section 2: Observations\n\nNone.\n\n"
        f"## Section 3: Overall Assessment\n\n{overall}\n"
        + (f"\n## Section 4: Fix Verification Results\n\n{claims}\n" if claims else "")
    )


def _claim_entry(
    claim_id: str,
    status: str,
    reason: str = "声明与当前 diff 一致。",
    evidence: str = "app.py 第 1 行已改为新值。",
) -> str:
    return (
        f"### {claim_id}\n"
        f"- **Status**: {status}\n"
        f"- **Reason**: {reason}\n"
        f"- **Evidence**: {evidence}\n"
    )


def _write_raw(locator: dict[str, str], value: str) -> None:
    Path(locator["raw_analysis_path"]).write_text(value, encoding="utf-8")


def _audit(locator: dict[str, str]) -> dict:
    return json.loads(
        (Path(locator["final_dir"]) / "audit.json").read_text(encoding="utf-8")
    )


def test_supported_claim_flow_writes_claims_provenance_and_single_run(
    tmp_path: Path,
) -> None:
    locator, source_bytes = _prepare_flow(
        tmp_path, (_target(demo_audit(), "finding-001", "缓存路径已修复"),)
    )
    prompt = (Path(locator["staging_dir"]) / ".run" / "prompt.md").read_text(
        encoding="utf-8"
    )
    assert "claim-001" in prompt
    assert "旧 token 仍可能被缓存层返回" in prompt
    assert "缓存路径已修复" in prompt
    assert "## Section 4: Fix Verification Results" in prompt
    assert "never prove a fix" in prompt

    _write_raw(
        locator,
        _raw(locator, claims=_claim_entry("claim-001", "supported")),
    )
    result = finalize_review(locator["final_dir"])

    audit = _audit(locator)
    assert result["review_status"] == "complete"
    run = audit["runs"][0]
    assert run["kind"] == "model_review"
    assert audit["runs"] == [run]
    assert run["summary_audit"] == {
        "status": "supported",
        "claims": [
            {
                "id": "claim-001",
                "text": "缓存路径已修复",
                "status": "supported",
                "reason": "声明与当前 diff 一致。",
            }
        ],
    }
    assert audit["summary"]["summary_audit_status"] == "supported"

    evidence = next(
        node for node in audit["nodes"] if node["id"] == "evidence-claim-001"
    )
    assert evidence["status"] == "pass"
    claim_edges = [
        edge
        for edge in audit["edges"]
        if edge["type"] in {"supports_claim", "challenges_claim"}
    ]
    assert claim_edges == [
        {
            "id": claim_edges[0]["id"],
            "type": "supports_claim",
            "from": "evidence-claim-001",
            "to": run["id"],
            "claim_id": "claim-001",
        }
    ]

    provenance = audit["extensions"]["evidentloop"]["fix_verification"]
    assert set(provenance) == {
        "version",
        "source_report_version",
        "source_diff_version",
        "targets",
    }
    assert provenance["version"] == 1
    assert provenance["source_diff_version"] == OLD_DIFF_VERSION
    assert provenance["source_report_version"] == content_version(source_bytes)
    assert provenance["targets"] == [
        {
            "claim_id": "claim-001",
            "finding_id": "finding-001",
            "fingerprint": demo_audit()["nodes"][3]["fingerprint"],
            "source_title": "旧 token 仍可能被缓存层返回",
            "claim": "缓存路径已修复",
        }
    ]
    serialized = json.dumps(audit, ensure_ascii=False)
    assert str(tmp_path) not in serialized

    html = (Path(locator["final_dir"]) / "audit.html").read_text(encoding="utf-8")
    assert "上一轮问题是否已解决" in html
    assert "旧 token 仍可能被缓存层返回" in html
    assert "缓存路径已修复" in html
    assert "声明与当前 diff 一致。" in html
    assert "认可 1" in html

    assert (Path(tmp_path / "source-audit.json")).read_bytes() == source_bytes


def test_mixed_diff_keeps_new_findings_and_claims_independent(tmp_path: Path) -> None:
    locator, _ = _prepare_flow(
        tmp_path, (_target(demo_audit(), "finding-002", "边界测试已补充"),)
    )
    finding_block = (
        "**f-001**\n"
        f"- **Where**: `app.py`, line 1, {_header(locator)}\n"
        "- **What**: 新常量缺少文档说明。\n"
        "- **Why**: 调用方无法从 diff 判断该值的约束。\n"
        "- **Severity estimate**: LOW\n"
        "- **Category**: missing_test\n"
    )
    _write_raw(
        locator,
        _raw(
            locator,
            findings=finding_block,
            overall="存在一个新问题，且旧问题声明未成立。",
            claims=_claim_entry(
                "claim-001",
                "challenged",
                reason="diff 中没有新增边界测试，声明未成立。",
                evidence="tests 文件未出现在 diff 中。",
            ),
        ),
    )
    result = finalize_review(locator["final_dir"])

    audit = _audit(locator)
    assert result["review_status"] == "complete"
    assert result["verdict"] == "concerns"
    assert audit["summary"]["finding_count"] == 1
    assert audit["summary"]["overall_severity"] is not None
    run = audit["runs"][0]
    assert run["summary_audit"]["status"] == "challenged"
    assert run["summary_audit"]["claims"][0]["status"] == "challenged"
    edge_types = {
        edge["type"] for edge in audit["edges"] if edge.get("claim_id") == "claim-001"
    }
    assert edge_types == {"challenges_claim"}


def test_four_claim_states_map_to_edges_and_aggregate(tmp_path: Path) -> None:
    audit_source = demo_audit()
    locator, _ = _prepare_flow(
        tmp_path,
        (
            _target(audit_source, "finding-001", "声明一"),
            _target(audit_source, "finding-002", "声明二"),
        ),
    )
    _write_raw(
        locator,
        _raw(
            locator,
            claims=(
                _claim_entry(
                    "claim-001", "partial", reason="部分路径已修复，缓存路径仍存疑。"
                )
                + _claim_entry(
                    "claim-002",
                    "unknown",
                    reason="diff 未覆盖该测试文件。",
                    evidence="none",
                )
            ),
        ),
    )
    finalize_review(locator["final_dir"])

    audit = _audit(locator)
    run = audit["runs"][0]
    assert run["summary_audit"]["status"] == "partial"
    claim_one_edges = sorted(
        edge["type"] for edge in audit["edges"] if edge.get("claim_id") == "claim-001"
    )
    assert claim_one_edges == ["challenges_claim", "supports_claim"]
    assert not any(edge.get("claim_id") == "claim-002" for edge in audit["edges"])
    assert not any(node["id"] == "evidence-claim-002" for node in audit["nodes"])


def test_same_state_claims_aggregate_to_that_state(tmp_path: Path) -> None:
    audit_source = demo_audit()
    locator, _ = _prepare_flow(
        tmp_path,
        (
            _target(audit_source, "finding-001", "声明一"),
            _target(audit_source, "finding-002", "声明二"),
        ),
    )
    _write_raw(
        locator,
        _raw(
            locator,
            claims=(
                _claim_entry("claim-001", "supported")
                + _claim_entry("claim-002", "supported")
            ),
        ),
    )
    finalize_review(locator["final_dir"])
    assert _audit(locator)["runs"][0]["summary_audit"]["status"] == "supported"


def test_incomplete_claim_block_downgrades_to_partial_but_keeps_provenance(
    tmp_path: Path,
) -> None:
    locator, _ = _prepare_flow(
        tmp_path, (_target(demo_audit(), "finding-001", "缓存路径已修复"),)
    )
    _write_raw(locator, _raw(locator))
    result = finalize_review(locator["final_dir"])

    audit = _audit(locator)
    assert result["review_status"] == "partial"
    assert result["verdict"] == "inconclusive"
    assert "summary_audit" not in audit["runs"][0]
    assert audit["summary"]["summary_audit_status"] == "not_audited"
    assert audit["extensions"]["evidentloop"]["fix_verification"]["version"] == 1
    html = (Path(locator["final_dir"]) / "audit.html").read_text(encoding="utf-8")
    assert "上一轮问题是否已解决" in html
    assert "缓存路径已修复" in html
    assert "未完成 1" in html
    assert "本轮没有生成该目标的有效验证结果" in html


@pytest.mark.parametrize(
    "claims",
    [
        _claim_entry("claim-001", "supported") + _claim_entry("claim-999", "supported"),
        _claim_entry("claim-001", "supported")
        + _claim_entry("claim-extra", "supported"),
        _claim_entry("claim-001", "supported")
        + "\n## Section 4: Fix Verification Results\n\n"
        + _claim_entry("claim-999", "supported"),
    ],
)
def test_unexpected_or_duplicate_claim_output_downgrades_to_partial(
    tmp_path: Path,
    claims: str,
) -> None:
    locator, _ = _prepare_flow(
        tmp_path, (_target(demo_audit(), "finding-001", "缓存路径已修复"),)
    )
    _write_raw(locator, _raw(locator, claims=claims))
    result = finalize_review(locator["final_dir"])
    assert result["review_status"] == "partial"


def test_normal_prepare_prompt_has_no_claims(tmp_path: Path) -> None:
    repo = initialized_repo(tmp_path)
    stage_simple_change(repo)
    from evidentloop.audit.finalize import prepare_local_diff

    locator = prepare_local_diff(repo, "staged", repo / "reports" / "plain")
    prompt = (Path(locator["staging_dir"]) / ".run" / "prompt.md").read_text(
        encoding="utf-8"
    )
    assert "(no fix verification claims)" in prompt
    assert "## Section 4: Fix Verification Results" in prompt
    assert "use the following required sections" in prompt
    assert "into two sections" not in prompt


def test_parser_reports_each_contract_violation() -> None:
    expected = ("claim-001", "claim-002")
    ok = (
        "## Section 4: Fix Verification Results\n\n"
        + _claim_entry("claim-002", "unknown", evidence="none")
        + _claim_entry("claim-001", "supported")
    )
    results, problems = parse_fix_verification_results(ok, expected)
    assert problems == []
    assert [item["claim_id"] for item in results] == ["claim-001", "claim-002"]

    _, missing = parse_fix_verification_results(
        "## Section 4: Fix Verification Results\n\n"
        + _claim_entry("claim-001", "supported"),
        expected,
    )
    assert any("missing result for claim_id: claim-002" in item for item in missing)

    _, unknown = parse_fix_verification_results(
        "## Section 4: Fix Verification Results\n\n"
        + _claim_entry("claim-777", "supported"),
        expected,
    )
    assert any("unknown claim_id" in item for item in unknown)

    _, duplicate = parse_fix_verification_results(
        "## Section 4: Fix Verification Results\n\n"
        + _claim_entry("claim-001", "supported")
        + _claim_entry("claim-001", "challenged")
        + _claim_entry("claim-002", "supported"),
        expected,
    )
    assert any("duplicate claim_id" in item for item in duplicate)

    _, bad_status = parse_fix_verification_results(
        "## Section 4: Fix Verification Results\n\n"
        + _claim_entry("claim-001", "fixed")
        + _claim_entry("claim-002", "supported"),
        expected,
    )
    assert any("invalid status" in item for item in bad_status)

    _, no_reason = parse_fix_verification_results(
        "## Section 4: Fix Verification Results\n\n"
        "### claim-001\n- **Status**: supported\n- **Evidence**: x\n"
        + _claim_entry("claim-002", "supported"),
        expected,
    )
    assert any("missing a non-empty Reason" in item for item in no_reason)

    _, supported_without_evidence = parse_fix_verification_results(
        "## Section 4: Fix Verification Results\n\n"
        + _claim_entry("claim-001", "supported", evidence="none"),
        ["claim-001"],
    )
    assert supported_without_evidence == [
        "claim-001 with supported status requires concrete Evidence"
    ]

    _, unknown_with_evidence = parse_fix_verification_results(
        "## Section 4: Fix Verification Results\n\n"
        + _claim_entry("claim-001", "unknown", evidence="app.py:1"),
        ["claim-001"],
    )
    assert unknown_with_evidence == [
        "claim-001 with unknown status must use Evidence: none"
    ]


@pytest.mark.parametrize(
    ("field", "duplicate", "expected_problem"),
    [
        ("Status", "challenged", "invalid status"),
        ("Reason", "另一项冲突原因。", "missing a non-empty Reason"),
        ("Evidence", "app.py 第 2 行。", "missing a non-empty Evidence"),
    ],
)
def test_parser_rejects_duplicate_claim_fields(
    field: str,
    duplicate: str,
    expected_problem: str,
) -> None:
    entry = _claim_entry("claim-001", "supported")
    first_line = next(
        line for line in entry.splitlines() if line.startswith(f"- **{field}**:")
    )
    conflicting = entry.replace(
        first_line,
        f"{first_line}\n- **{field}**: {duplicate}",
    )

    results, problems = parse_fix_verification_results(
        f"## Section 4: Fix Verification Results\n\n{conflicting}",
        ["claim-001"],
    )

    assert results == []
    assert any(expected_problem in problem for problem in problems)


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ((), "not_audited"),
        (("supported",), "supported"),
        (("challenged", "challenged"), "challenged"),
        (("supported", "challenged"), "partial"),
        (("unknown", "supported"), "partial"),
    ],
)
def test_aggregate_claim_status(statuses: tuple[str, ...], expected: str) -> None:
    assert aggregate_claim_status(statuses) == expected


def test_validation_enforces_claim_edge_truth_table() -> None:
    audit = demo_audit()
    audit["runs"][0]["summary_audit"]["claims"][0]["status"] = "supported"
    issues = validate_audit(audit)
    codes = {issue.code for issue in issues}
    assert "claim.status_mismatch" in codes


def test_validation_enforces_claim_status_aggregates() -> None:
    audit = demo_audit()
    audit["runs"][0]["summary_audit"]["status"] = "supported"
    audit["summary"]["summary_audit_status"] = "supported"

    issues = validate_audit(audit)
    codes = {issue.code for issue in issues}

    assert "claim.summary_status_mismatch" in codes
    assert "claim.report_status_mismatch" in codes


def test_validation_cross_checks_provenance_targets() -> None:
    audit = demo_audit()
    audit.setdefault("extensions", {}).setdefault("evidentloop", {})[
        "fix_verification"
    ] = {
        "version": 1,
        "source_report_version": "sha256:" + "b" * 64,
        "source_diff_version": OLD_DIFF_VERSION,
        "targets": [
            {
                "claim_id": "claim-001",
                "finding_id": "finding-001",
                "fingerprint": audit["nodes"][3]["fingerprint"],
                "source_title": "旧 token 仍可能被缓存层返回",
                "claim": "与冻结声明不同的文本",
            }
        ],
    }
    issues = validate_audit(audit)
    codes = {issue.code for issue in issues}
    assert "claim.target_mismatch" in codes

    audit["extensions"]["evidentloop"]["fix_verification"]["version"] = 2
    audit["extensions"]["evidentloop"]["fix_verification"]["absolute_path"] = "/tmp/x"
    issues = validate_audit(audit)
    assert any(issue.code == "fix_verification.invalid_provenance" for issue in issues)

    complete_without_claims = demo_audit()
    model_run = complete_without_claims["runs"][0]
    model_run.pop("summary_audit")
    complete_without_claims["summary"]["summary_audit_status"] = "not_audited"
    complete_without_claims["edges"] = [
        edge
        for edge in complete_without_claims["edges"]
        if edge["type"] not in {"supports_claim", "challenges_claim"}
    ]
    complete_without_claims.setdefault("extensions", {}).setdefault("evidentloop", {})[
        "fix_verification"
    ] = {
        "version": 1,
        "source_report_version": "sha256:" + "b" * 64,
        "source_diff_version": OLD_DIFF_VERSION,
        "targets": [
            {
                "claim_id": "claim-001",
                "finding_id": "finding-001",
                "fingerprint": complete_without_claims["nodes"][3]["fingerprint"],
                "source_title": "旧 token 仍可能被缓存层返回",
                "claim": "token refresh 已完全修复，过期 token 不再返回",
            }
        ],
    }
    issues = validate_audit(complete_without_claims)
    assert any(issue.code == "claim.target_mismatch" for issue in issues)


def test_validation_requires_fix_verification_to_reference_a_new_diff() -> None:
    audit = demo_audit()
    audit.setdefault("extensions", {}).setdefault("evidentloop", {})[
        "fix_verification"
    ] = {
        "version": 1,
        "source_report_version": "sha256:" + "b" * 64,
        "source_diff_version": OLD_DIFF_VERSION,
        "targets": [
            {
                "claim_id": "claim-001",
                "finding_id": "finding-001",
                "fingerprint": audit["nodes"][3]["fingerprint"],
                "source_title": "旧 token 仍可能被缓存层返回",
                "claim": audit["runs"][0]["summary_audit"]["claims"][0]["text"],
            }
        ],
    }
    audit["extensions"]["evidentloop"]["diff_version"] = OLD_DIFF_VERSION
    issues = validate_audit(audit)
    assert any(issue.code == "fix_verification.same_diff" for issue in issues)

    audit["extensions"]["evidentloop"].pop("diff_version")
    issues = validate_audit(audit)
    assert any(
        issue.code == "fix_verification.missing_current_diff" for issue in issues
    )


def test_cli_prepare_accepts_fix_verification_request_document(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = initialized_repo(tmp_path)
    stage_simple_change(repo)
    source = tmp_path / "source-audit.json"
    version, audit = _write_source(source)
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "source_audit_json": str(source),
                "expected_source_report_version": version,
                "targets": [
                    {
                        "finding_id": "finding-001",
                        "fingerprint": audit["nodes"][3]["fingerprint"],
                        "claim": "缓存路径已修复",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(repo)

    assert (
        main(
            [
                "prepare",
                "--diff",
                "staged",
                "--fix-verification",
                str(request_path),
                "--out",
                "reports/cli-fv",
            ]
        )
        == 0
    )
    locator = json.loads(capsys.readouterr().out)
    skeleton = json.loads(
        (Path(locator["staging_dir"]) / ".run" / "audit-skeleton.json").read_text(
            encoding="utf-8"
        )
    )
    assert skeleton["fix_verification"]["targets"][0]["claim_id"] == "claim-001"


def test_cli_prepare_rejects_malformed_request_document(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = initialized_repo(tmp_path)
    stage_simple_change(repo)
    request_path = tmp_path / "bad-request.json"
    request_path.write_text(
        json.dumps({"source_audit_json": "x.json", "targets": []}),
        encoding="utf-8",
    )
    monkeypatch.chdir(repo)

    assert (
        main(
            [
                "prepare",
                "--diff",
                "staged",
                "--fix-verification",
                str(request_path),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert "missing fields" in captured.err
    assert not (repo / "reports").exists()


def test_request_deserializer_is_strict() -> None:
    valid = {
        "source_audit_json": "audit.json",
        "expected_source_report_version": "sha256:" + "a" * 64,
        "targets": [
            {
                "finding_id": "finding-001",
                "fingerprint": "sha256:" + "b" * 64,
                "claim": "已修复",
            }
        ],
    }
    request = fix_verification_request_from_dict(valid)
    assert request.targets[0].finding_id == "finding-001"

    from evidentloop.audit.finalize import AuditWorkflowError

    with pytest.raises(AuditWorkflowError, match="unknown fields"):
        fix_verification_request_from_dict({**valid, "extra": 1})
    with pytest.raises(AuditWorkflowError, match="missing fields"):
        fix_verification_request_from_dict({"source_audit_json": "x"})
    with pytest.raises(AuditWorkflowError, match="non-empty list"):
        fix_verification_request_from_dict({**valid, "targets": []})
    with pytest.raises(AuditWorkflowError, match="target 1 field claim"):
        fix_verification_request_from_dict(
            {
                **valid,
                "targets": [
                    {
                        "finding_id": "finding-001",
                        "fingerprint": "sha256:" + "b" * 64,
                        "claim": "  ",
                    }
                ],
            }
        )
    with pytest.raises(AuditWorkflowError, match="expected_source_report_version"):
        fix_verification_request_from_dict(
            {**valid, "expected_source_report_version": "latest"}
        )
    with pytest.raises(AuditWorkflowError, match="target 1 fingerprint"):
        fix_verification_request_from_dict(
            {
                **valid,
                "targets": [{**valid["targets"][0], "fingerprint": "stale"}],
            }
        )
