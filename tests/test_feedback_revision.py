"""Feedback parsing, revision semantics, and report-pair recovery tests."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

import evidentloop.audit.revision as revision_module
from evidentloop.audit.feedback import (
    FeedbackError,
    normalize_feedback,
    parse_feedback_jsonl,
)
from evidentloop.audit.revision import (
    RevisionError,
    audit_sha256,
    build_feedback_revision,
    recover_interrupted_revision,
    revise_audit,
)
from evidentloop.audit.summary import build_summary
from evidentloop.cli import main
from evidentloop.renderers.html import render_audit_file
from evidentloop.validation import assert_valid_audit, validate_audit
from tests.audit_helpers import demo_audit, minimal_audit


DIFF_VERSION = "sha256:" + "a" * 64


def _versioned_audit() -> dict:
    audit = demo_audit()
    audit.setdefault("extensions", {}).setdefault("evidentloop", {})[
        "diff_version"
    ] = DIFF_VERSION
    return audit


def _write_report(report_dir: Path, audit: dict | None = None) -> tuple[dict, str]:
    report_dir.mkdir(parents=True)
    value = copy.deepcopy(audit or demo_audit())
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    (report_dir / "audit.json").write_bytes(raw)
    render_audit_file(report_dir / "audit.json", report_dir / "audit.html")
    return value, audit_sha256(raw)


def _event(
    audit: dict,
    target_id: str,
    action: str,
    *,
    source_hash: str | None = None,
    **value,
) -> dict:
    finding = next(node for node in audit["nodes"] if node.get("id") == target_id)
    event = {
        "target_type": "finding",
        "target_id": target_id,
        "action": action,
        "fingerprint": finding["fingerprint"],
        "graph_id": audit["graph_id"],
        "run_id": audit["runs"][-1]["id"],
        "created_at": "2026-07-17T10:00:00+08:00",
        **value,
    }
    if source_hash is not None:
        event["source_audit_sha256"] = source_hash
    return event


def _feedback_file(path: Path, events: list[dict]) -> Path:
    path.write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )
    return path


def test_parser_is_strict_and_preserves_untrusted_comment() -> None:
    audit = demo_audit()
    attack = '</script><script data-attack="1">alert(1)</script>\n第二行'
    event = _event(audit, "finding-001", "comment", comment=attack)
    raw = (json.dumps(event, ensure_ascii=False) + "\n").encode()

    assert parse_feedback_jsonl(raw)[0]["comment"] == attack

    missing_value = _event(audit, "finding-001", "comment")
    with pytest.raises(FeedbackError, match="missing fields: comment"):
        parse_feedback_jsonl((json.dumps(missing_value) + "\n").encode())

    unknown = {**event, "unexpected": True}
    with pytest.raises(FeedbackError, match="unknown fields"):
        parse_feedback_jsonl((json.dumps(unknown) + "\n").encode())


@pytest.mark.parametrize(
    ("action", "extra", "code"),
    [
        (["accept"], {}, "feedback.invalid_action"),
        ("severity_override", {"severity": ["high"]}, "feedback.invalid_severity"),
        ("comment", {"comment": "x" * 4_001}, "feedback.comment_too_long"),
        (
            "comment",
            {"comment": "ok", "created_at": "not-a-time"},
            "feedback.invalid_timestamp",
        ),
    ],
)
def test_parser_rejects_non_scalar_and_out_of_bounds_values(
    action: object,
    extra: dict,
    code: str,
) -> None:
    audit = demo_audit()
    event = _event(audit, "finding-001", "accept")
    event.update({"action": action, **extra})

    with pytest.raises(FeedbackError) as captured:
        parse_feedback_jsonl((json.dumps(event) + "\n").encode())

    assert captured.value.code == code


def test_normalizer_deduplicates_exact_events_and_rejects_conflicts() -> None:
    audit = demo_audit()
    accepted = _event(audit, "finding-001", "accept")
    normalized, _ = normalize_feedback([accepted, accepted])
    assert normalized == [accepted]

    false_positive = _event(audit, "finding-001", "false_positive")
    with pytest.raises(FeedbackError, match="multiple disposition"):
        normalize_feedback([accepted, false_positive])


def test_summary_pure_function_preserves_initial_audit_result() -> None:
    audit = minimal_audit()
    calculated = build_summary(
        (node for node in audit["nodes"] if node["type"] == "finding"),
        (node for node in audit["nodes"] if node["type"] == "fix"),
        review_status=audit["summary"]["review_status"],
        empty_verdict="pass_candidate",
    )
    for field in (
        "verdict",
        "risk_score",
        "finding_count",
        "unscored_finding_count",
        "open_finding_count",
        "fix_count",
        "fix_done_count",
    ):
        assert calculated[field] == audit["summary"][field]


def test_v04_revision_preserves_model_judgment() -> None:
    source = demo_audit()
    source_raw = (json.dumps(source, ensure_ascii=False, indent=2) + "\n").encode()
    source_hash = audit_sha256(source_raw)
    events = [
        _event(source, "finding-001", "false_positive", source_hash=source_hash),
        _event(source, "finding-002", "false_positive", source_hash=source_hash),
    ]
    normalized, _ = normalize_feedback(events)

    revised = build_feedback_revision(
        source,
        normalized,
        source_hash=source_hash,
    )

    assert revised["schema_version"] == "0.4"
    assert revised["summary"]["verdict"] == "pass_candidate"
    assert revised["summary"]["model_verdict"] == "concerns"
    assert revised["summary"]["notice"] == "基于人工裁定，未重新审查代码"
    finding = next(node for node in revised["nodes"] if node["id"] == "finding-001")
    assert finding["status"] == "dismissed"
    assert finding["model_judgment"] == {"status": "open", "severity": "high"}
    assert finding["human_adjudication"]["disposition"] == "false_positive"
    assert validate_audit(revised) == []


def test_second_revision_can_undo_comment_severity_and_disposition() -> None:
    source = demo_audit()
    first_source_hash = audit_sha256(json.dumps(source, sort_keys=True).encode())
    first_events = [
        _event(source, "finding-001", "false_positive"),
        _event(source, "finding-001", "comment", comment="误报依据"),
        _event(source, "finding-001", "severity_override", severity="low"),
    ]
    first_events, _ = normalize_feedback(first_events)
    first = build_feedback_revision(
        source,
        first_events,
        source_hash=first_source_hash,
    )
    second_source_hash = audit_sha256(json.dumps(first, sort_keys=True).encode())
    second_events = [
        _event(first, "finding-001", "accept"),
        _event(first, "finding-001", "comment", comment=None),
        _event(first, "finding-001", "severity_override", severity=None),
    ]
    second_events, _ = normalize_feedback(second_events)

    second = build_feedback_revision(
        first,
        second_events,
        source_hash=second_source_hash,
    )

    finding = next(node for node in second["nodes"] if node["id"] == "finding-001")
    assert finding["status"] == "open"
    assert finding["severity"] == "high"
    assert finding["human_adjudication"]["disposition"] == "accept"
    assert "comment" not in finding["human_adjudication"]
    assert "severity_override" not in finding["human_adjudication"]
    assert_valid_audit(second)


def test_clearing_the_only_current_human_value_removes_adjudication() -> None:
    source = demo_audit()
    source_hash = audit_sha256(json.dumps(source, sort_keys=True).encode())
    first_events, _ = normalize_feedback(
        [_event(source, "finding-001", "comment", comment="temporary")]
    )
    first = build_feedback_revision(
        source,
        first_events,
        source_hash=source_hash,
    )
    assert first["summary"]["risk_score"] == source["summary"]["risk_score"]
    assert first["summary"]["verdict"] == source["summary"]["verdict"]
    second_events, _ = normalize_feedback(
        [_event(first, "finding-001", "comment", comment=None)]
    )
    second = build_feedback_revision(
        first,
        second_events,
        source_hash=audit_sha256(json.dumps(first, sort_keys=True).encode()),
    )

    finding = next(node for node in second["nodes"] if node["id"] == "finding-001")
    assert "human_adjudication" not in finding
    assert_valid_audit(second)


def test_incomplete_source_cannot_become_pass_candidate() -> None:
    source = demo_audit()
    source["summary"].update(
        {"review_status": "partial", "verdict": "inconclusive", "risk_score": None}
    )
    source["runs"][-1]["status"] = "inconclusive"
    source_hash = audit_sha256(json.dumps(source, sort_keys=True).encode())
    events, _ = normalize_feedback(
        [
            _event(source, "finding-001", "false_positive"),
            _event(source, "finding-002", "false_positive"),
        ]
    )

    revised = build_feedback_revision(
        source,
        events,
        source_hash=source_hash,
    )

    assert revised["summary"]["verdict"] == "inconclusive"
    assert revised["summary"]["risk_score"] is None


def test_semantic_validation_detects_tampered_revision_state() -> None:
    source = demo_audit()
    source_hash = audit_sha256(json.dumps(source, sort_keys=True).encode())
    events, _ = normalize_feedback([_event(source, "finding-001", "false_positive")])
    revised = build_feedback_revision(
        source,
        events,
        source_hash=source_hash,
    )
    finding = next(node for node in revised["nodes"] if node["id"] == "finding-001")
    finding["status"] = "open"

    issues = validate_audit(revised)

    assert any(issue.code == "revision.finding_state_mismatch" for issue in issues)


def test_semantic_validation_detects_tampered_feedback_hash() -> None:
    source = demo_audit()
    source_hash = audit_sha256(json.dumps(source, sort_keys=True).encode())
    events, _ = normalize_feedback([_event(source, "finding-001", "false_positive")])
    revised = build_feedback_revision(source, events, source_hash=source_hash)
    revised["runs"][-1]["revision"]["feedback_sha256"] = "sha256:" + "0" * 64

    issues = validate_audit(revised)

    assert any(issue.code == "revision.feedback_hash_mismatch" for issue in issues)


def test_model_only_report_rejects_human_summary_claims() -> None:
    audit = demo_audit()
    audit["schema_version"] = "0.4"
    for run in audit["runs"]:
        run["kind"] = "model_review"
    for finding in (node for node in audit["nodes"] if node["type"] == "finding"):
        finding["model_judgment"] = {
            "status": finding["status"],
            "severity": finding["severity"],
        }
    audit["summary"]["basis"] = "model_review"
    assert_valid_audit(audit)

    audit["summary"].update(
        {
            "basis": "human_adjudication",
            "risk_delta": 0,
            "model_verdict": audit["summary"]["verdict"],
            "model_risk_score": audit["summary"]["risk_score"],
            "notice": "基于人工裁定，未重新审查代码",
        }
    )

    issue_codes = {issue.code for issue in validate_audit(audit)}
    assert "revision.model_summary_basis" in issue_codes
    assert "revision.orphan_human_summary" in issue_codes


def test_repeating_current_disposition_is_not_a_revision() -> None:
    source = demo_audit()
    first_events, _ = normalize_feedback(
        [_event(source, "finding-001", "false_positive")]
    )
    first = build_feedback_revision(
        source,
        first_events,
        source_hash=audit_sha256(json.dumps(source, sort_keys=True).encode()),
    )
    repeated_events, _ = normalize_feedback(
        [_event(first, "finding-001", "false_positive")]
    )

    with pytest.raises(RevisionError) as captured:
        build_feedback_revision(
            first,
            repeated_events,
            source_hash=audit_sha256(json.dumps(first, sort_keys=True).encode()),
        )

    assert captured.value.code == "revision.no_change"


def test_revise_updates_pair_in_place_and_explicit_out_preserves_source(
    tmp_path: Path,
) -> None:
    report = tmp_path / "report"
    source, _ = _write_report(report, _versioned_audit())
    note = report / "notes.txt"
    note.write_text("keep me", encoding="utf-8")
    report_inode = report.stat().st_ino
    note_inode = note.stat().st_ino
    feedback = _feedback_file(
        tmp_path / "feedback.jsonl",
        [_event(source, "finding-001", "false_positive")],
    )

    copy_result = revise_audit(report / "audit.json", feedback, tmp_path / "copy")
    assert copy_result["mode"] == "copy"
    assert copy_result["diff_version"] == DIFF_VERSION
    assert copy_result["report_version"] == audit_sha256(
        (tmp_path / "copy" / "audit.json").read_bytes()
    )
    assert json.loads((report / "audit.json").read_text())["schema_version"] == "0.4"
    assert (
        json.loads((tmp_path / "copy" / "audit.json").read_text())["schema_version"]
        == "0.4"
    )

    in_place_result = revise_audit(report / "audit.json", feedback)
    assert in_place_result["mode"] == "in_place"
    assert in_place_result["diff_version"] == DIFF_VERSION
    assert in_place_result["report_version"] == audit_sha256(
        (report / "audit.json").read_bytes()
    )
    assert json.loads((report / "audit.json").read_text())["schema_version"] == "0.4"
    assert (report / "audit.html").is_file()
    assert report.stat().st_ino == report_inode
    assert note.read_text(encoding="utf-8") == "keep me"
    assert note.stat().st_ino == note_inode
    assert validate_audit(json.loads((report / "audit.json").read_text())) == []


def test_revise_legacy_v04_report_returns_unknown_diff_version(
    tmp_path: Path,
) -> None:
    report = tmp_path / "report"
    source, _ = _write_report(report)
    feedback = _feedback_file(
        tmp_path / "feedback.jsonl",
        [_event(source, "finding-001", "false_positive")],
    )

    result = revise_audit(report / "audit.json", feedback)

    assert result["diff_version"] is None
    assert result["report_version"] == audit_sha256(
        (report / "audit.json").read_bytes()
    )


def test_revise_rejects_historical_schema_source(tmp_path: Path) -> None:
    historical = (
        Path(__file__).resolve().parents[1]
        / "docs/examples/evidentloop-alpha/audit.json"
    )
    report = tmp_path / "historical"
    report.mkdir()
    (report / "audit.json").write_bytes(historical.read_bytes())

    with pytest.raises(RevisionError) as captured:
        revise_audit(report / "audit.json", tmp_path / "unused.jsonl")

    assert captured.value.code == "revision.unsupported_schema"
    assert "generate a new report" in captured.value.message


def test_two_round_report_revision_replays_only_the_new_delta(tmp_path: Path) -> None:
    report = tmp_path / "report"
    source, source_hash = _write_report(report, _versioned_audit())
    first_feedback = _feedback_file(
        tmp_path / "first.jsonl",
        [
            _event(
                source,
                "finding-001",
                "false_positive",
                source_hash=source_hash,
            ),
            _event(
                source,
                "finding-001",
                "comment",
                source_hash=source_hash,
                comment="第一轮依据",
            ),
            _event(
                source,
                "finding-001",
                "severity_override",
                source_hash=source_hash,
                severity="low",
            ),
        ],
    )

    first_result = revise_audit(report / "audit.json", first_feedback)
    first = json.loads((report / "audit.json").read_text(encoding="utf-8"))
    first_hash = audit_sha256((report / "audit.json").read_bytes())
    second_feedback = _feedback_file(
        tmp_path / "second.jsonl",
        [
            _event(first, "finding-001", "accept", source_hash=first_hash),
            _event(
                first,
                "finding-001",
                "comment",
                source_hash=first_hash,
                comment=None,
            ),
            _event(
                first,
                "finding-001",
                "severity_override",
                source_hash=first_hash,
                severity=None,
            ),
        ],
    )

    second_result = revise_audit(report / "audit.json", second_feedback)
    second = json.loads((report / "audit.json").read_text(encoding="utf-8"))
    finding = next(node for node in second["nodes"] if node["id"] == "finding-001")
    html = (report / "audit.html").read_text(encoding="utf-8")

    assert first_result["revision_run_id"] != second_result["revision_run_id"]
    assert (
        first_result["diff_version"]
        == second_result["diff_version"]
        == DIFF_VERSION
    )
    assert first_result["report_version"] != second_result["report_version"]
    assert second_result["report_version"] == audit_sha256(
        (report / "audit.json").read_bytes()
    )
    assert [run["kind"] for run in second["runs"]] == [
        "model_review",
        "feedback_revision",
        "feedback_revision",
    ]
    assert finding["status"] == "open"
    assert finding["severity"] == finding["model_judgment"]["severity"] == "high"
    assert finding["human_adjudication"] == {
        "disposition": "accept",
        "applied_run_id": second_result["revision_run_id"],
    }
    assert (
        second["runs"][-1]["revision"]["source_run_id"]
        == first_result["revision_run_id"]
    )
    assert "第一轮依据" not in html
    assert "模型原判断" in html
    assert "我的裁定" in html
    assert "当前剩余问题" in html
    assert f'data-run-id="{second_result["revision_run_id"]}"' in html
    assert validate_audit(second) == []


def test_explicit_out_rejects_nested_path_and_wraps_parent_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = tmp_path / "report"
    source, source_hash = _write_report(report)
    feedback = _feedback_file(
        tmp_path / "feedback.jsonl",
        [_event(source, "finding-001", "false_positive", source_hash=source_hash)],
    )
    before = (report / "audit.json").read_bytes(), (report / "audit.html").read_bytes()

    with pytest.raises(RevisionError) as captured:
        revise_audit(report / "audit.json", feedback, report / "copy")
    assert captured.value.code == "revision.invalid_output_path"

    for reserved in (
        tmp_path / ".report.evidentloop-revise-candidate",
        tmp_path / ".report.evidentloop-revise-backup",
    ):
        with pytest.raises(RevisionError) as captured:
            revise_audit(report / "audit.json", feedback, reserved)
        assert captured.value.code == "revision.invalid_output_path"
        assert not reserved.exists()

    blocked_parent = tmp_path / "not-a-directory"
    blocked_parent.write_text("occupied", encoding="utf-8")
    exit_code = main(
        [
            "revise",
            str(report / "audit.json"),
            "--feedback",
            str(feedback),
            "--out",
            str(blocked_parent / "copy"),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["code"] == "revision.output_parent_failed"
    assert str(blocked_parent) in payload["paths"]
    assert before == (
        (report / "audit.json").read_bytes(),
        (report / "audit.html").read_bytes(),
    )


def test_stale_hash_and_conflict_fail_without_touching_source(tmp_path: Path) -> None:
    report = tmp_path / "report"
    source, _ = _write_report(report)
    before = (report / "audit.json").read_bytes(), (report / "audit.html").read_bytes()
    stale = _feedback_file(
        tmp_path / "stale.jsonl",
        [_event(source, "finding-001", "accept", source_hash="sha256:" + "0" * 64)],
    )

    with pytest.raises(RevisionError, match="stale_feedback"):
        revise_audit(report / "audit.json", stale)
    assert before == (
        (report / "audit.json").read_bytes(),
        (report / "audit.html").read_bytes(),
    )

    conflict = _feedback_file(
        tmp_path / "conflict.jsonl",
        [
            _event(source, "finding-001", "accept"),
            _event(source, "finding-001", "false_positive"),
        ],
    )
    with pytest.raises(RevisionError, match="feedback.conflict"):
        revise_audit(report / "audit.json", conflict)
    assert before == (
        (report / "audit.json").read_bytes(),
        (report / "audit.html").read_bytes(),
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("graph_id", "audit:other"),
        ("run_id", "run-other"),
        ("target_id", "finding-missing"),
        ("fingerprint", "sha256:" + "b" * 64),
    ],
)
def test_source_identity_mismatch_fails_closed(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    report = tmp_path / "report"
    source, source_hash = _write_report(report)
    event = _event(
        source,
        "finding-001",
        "accept",
        source_hash=source_hash,
    )
    event[field] = value
    feedback = _feedback_file(tmp_path / "feedback.jsonl", [event])
    before = (report / "audit.json").read_bytes(), (report / "audit.html").read_bytes()

    with pytest.raises(RevisionError) as captured:
        revise_audit(report / "audit.json", feedback)

    assert captured.value.code == "revision.stale_feedback"
    assert before == (
        (report / "audit.json").read_bytes(),
        (report / "audit.html").read_bytes(),
    )


def test_cli_revise_failure_is_structured_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = tmp_path / "report"
    source, _ = _write_report(report)
    feedback = _feedback_file(
        tmp_path / "feedback.jsonl",
        [
            _event(
                source,
                "finding-001",
                "accept",
                source_hash="sha256:" + "0" * 64,
            )
        ],
    )

    exit_code = main(
        ["revise", str(report / "audit.json"), "--feedback", str(feedback)]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload == {
        "status": "error",
        "code": "revision.stale_feedback",
        "message": (
            "source audit changed after feedback was copied; "
            "refresh the report and copy again"
        ),
        "paths": [],
    }

    malformed = _event(source, "finding-001", "comment", comment="ok")
    malformed["unexpected"] = True
    feedback.write_text("\n" + json.dumps(malformed) + "\n", encoding="utf-8")

    assert (
        main(["revise", str(report / "audit.json"), "--feedback", str(feedback)]) == 1
    )
    malformed_payload = json.loads(capsys.readouterr().out)
    assert malformed_payload["code"] == "feedback.unknown_field"
    assert malformed_payload["message"].startswith("line 2:")


def test_pair_switch_failure_restores_old_pair_and_keeps_other_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    report = tmp_path / "report"
    source, source_hash = _write_report(report)
    feedback = _feedback_file(
        tmp_path / "feedback.jsonl",
        [_event(source, "finding-001", "false_positive", source_hash=source_hash)],
    )
    before = (report / "audit.json").read_bytes(), (report / "audit.html").read_bytes()
    note = report / "notes.txt"
    note.write_text("keep me", encoding="utf-8")
    candidate = tmp_path / ".report.evidentloop-revise-candidate"
    original_replace = os.replace
    failed = False

    def fail_candidate_swap(source_path, target_path):
        nonlocal failed
        if (
            not failed
            and Path(source_path) == candidate / "audit.json"
            and Path(target_path) == report / "audit.json"
        ):
            failed = True
            raise OSError("forced candidate swap failure")
        return original_replace(source_path, target_path)

    monkeypatch.setattr("evidentloop.audit.revision.os.replace", fail_candidate_swap)

    with pytest.raises(RevisionError, match="old report restored"):
        revise_audit(report / "audit.json", feedback)

    assert before == (
        (report / "audit.json").read_bytes(),
        (report / "audit.html").read_bytes(),
    )
    assert note.read_text(encoding="utf-8") == "keep me"
    assert not candidate.exists()
    assert not (tmp_path / ".report.evidentloop-revise-backup").exists()
    recovered = recover_interrupted_revision(report)
    assert recovered["status"] == "clean"


def test_post_swap_validation_failure_restores_old_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = tmp_path / "report"
    source, source_hash = _write_report(report)
    feedback = _feedback_file(
        tmp_path / "feedback.jsonl",
        [_event(source, "finding-001", "false_positive", source_hash=source_hash)],
    )
    before = (report / "audit.json").read_bytes(), (report / "audit.html").read_bytes()
    copy_target = tmp_path / "copy"
    original_is_valid = revision_module._report_is_valid

    def reject_committed_revision(path: Path) -> bool:
        candidate = Path(path)
        if candidate in {report, copy_target} and (candidate / "audit.json").is_file():
            audit = json.loads((candidate / "audit.json").read_text())
            if len(audit["runs"]) > 1:
                return False
        return original_is_valid(candidate)

    monkeypatch.setattr(
        "evidentloop.audit.revision._report_is_valid", reject_committed_revision
    )

    with pytest.raises(RevisionError) as captured:
        revise_audit(report / "audit.json", feedback)

    assert captured.value.code == "revision.commit_invalid"
    assert before == (
        (report / "audit.json").read_bytes(),
        (report / "audit.html").read_bytes(),
    )
    assert not (tmp_path / ".report.evidentloop-revise-backup").exists()

    with pytest.raises(RevisionError) as captured:
        revise_audit(report / "audit.json", feedback, copy_target)

    copy_staging = tmp_path / ".copy.evidentloop-staging"
    assert captured.value.code == "revision.commit_invalid"
    assert captured.value.paths == (copy_staging,)
    assert not copy_target.exists()
    assert copy_staging.is_dir()


def test_candidate_render_failure_never_touches_source_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = tmp_path / "report"
    source, source_hash = _write_report(report)
    feedback = _feedback_file(
        tmp_path / "feedback.jsonl",
        [_event(source, "finding-001", "false_positive", source_hash=source_hash)],
    )
    before = (report / "audit.json").read_bytes(), (report / "audit.html").read_bytes()

    def fail_render(*_args, **_kwargs):
        raise ValueError("forced render failure")

    monkeypatch.setattr("evidentloop.audit.revision.render_audit_file", fail_render)

    with pytest.raises(RevisionError, match="candidate_failed"):
        revise_audit(report / "audit.json", feedback)

    assert before == (
        (report / "audit.json").read_bytes(),
        (report / "audit.html").read_bytes(),
    )
    assert (
        recover_interrupted_revision(report)["status"] == "discarded_invalid_residuals"
    )


def test_interruption_recovery_matrix(tmp_path: Path) -> None:
    report = tmp_path / "report"
    source, source_hash = _write_report(report)
    events, _ = normalize_feedback(
        [_event(source, "finding-001", "false_positive", source_hash=source_hash)]
    )
    candidate_audit = build_feedback_revision(
        source,
        events,
        source_hash=source_hash,
    )
    candidate = tmp_path / ".report.evidentloop-revise-candidate"
    backup = tmp_path / ".report.evidentloop-revise-backup"
    note = report / "notes.txt"
    note.write_text("keep me", encoding="utf-8")
    _write_report(candidate, candidate_audit)
    revision_module._copy_report_pair(report, backup)
    os.replace(candidate / "audit.json", report / "audit.json")

    restored = recover_interrupted_revision(report)

    assert restored["status"] == "restored_old_report"
    assert note.read_text(encoding="utf-8") == "keep me"
    assert not candidate.exists() and not backup.exists()

    _write_report(candidate, candidate_audit)
    revision_module._copy_report_pair(report, backup)
    discarded = recover_interrupted_revision(report)
    assert discarded["status"] == "discarded_uncommitted_candidate"
    assert not candidate.exists() and not backup.exists()

    candidate.mkdir()
    (candidate / "broken").write_text("diagnostic", encoding="utf-8")
    continued = recover_interrupted_revision(report)
    assert continued["status"] == "discarded_invalid_residuals"
    assert report.is_dir() and not candidate.exists()


def test_revise_from_backup_path_restores_then_completes_update(tmp_path: Path) -> None:
    report = tmp_path / "report"
    source, source_hash = _write_report(report, _versioned_audit())
    events = [_event(source, "finding-001", "false_positive", source_hash=source_hash)]
    feedback = _feedback_file(tmp_path / "feedback.jsonl", events)
    normalized, _ = normalize_feedback(events)
    revised = build_feedback_revision(source, normalized, source_hash=source_hash)
    candidate = tmp_path / ".report.evidentloop-revise-candidate"
    backup = tmp_path / ".report.evidentloop-revise-backup"
    _write_report(candidate, revised)
    revision_module._copy_report_pair(report, backup)
    os.replace(candidate / "audit.json", report / "audit.json")

    result = revise_audit(backup / "audit.json", feedback)

    assert result["recovery"] == "restored_old_report"
    assert result["diff_version"] == DIFF_VERSION
    assert result["report_version"] == audit_sha256(
        (report / "audit.json").read_bytes()
    )
    assert result["report_dir"] == str(report)
    assert report.is_dir() and not candidate.exists() and not backup.exists()
    assert (
        json.loads((report / "audit.json").read_text())["runs"][-1]["id"]
        == result["revision_run_id"]
    )


def test_post_swap_interruption_keeps_new_pair_and_cleans_backup(
    tmp_path: Path,
) -> None:
    report = tmp_path / "report"
    source, source_hash = _write_report(report)
    events, _ = normalize_feedback(
        [_event(source, "finding-001", "false_positive", source_hash=source_hash)]
    )
    revised = build_feedback_revision(
        source,
        events,
        source_hash=source_hash,
    )
    candidate = tmp_path / ".report.evidentloop-revise-candidate"
    backup = tmp_path / ".report.evidentloop-revise-backup"
    _write_report(candidate, revised)
    revision_module._copy_report_pair(report, backup)
    revision_module._replace_report_pair(candidate, report)

    recovered = recover_interrupted_revision(report)

    assert recovered["status"] == "completed_new_report"
    assert report.is_dir() and not backup.exists()


def test_revise_from_backup_path_confirms_already_committed_feedback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = tmp_path / "report"
    source, source_hash = _write_report(report)
    events = [_event(source, "finding-001", "false_positive", source_hash=source_hash)]
    feedback = _feedback_file(tmp_path / "feedback.jsonl", events)
    normalized, _ = normalize_feedback(events)
    revised = build_feedback_revision(source, normalized, source_hash=source_hash)
    candidate = tmp_path / ".report.evidentloop-revise-candidate"
    backup = tmp_path / ".report.evidentloop-revise-backup"
    _write_report(candidate, revised)
    revision_module._copy_report_pair(report, backup)
    revision_module._replace_report_pair(candidate, report)
    committed = (
        (report / "audit.json").read_bytes(),
        (report / "audit.html").read_bytes(),
    )

    assert (
        main(["revise", str(backup / "audit.json"), "--feedback", str(feedback)]) == 0
    )
    result = json.loads(capsys.readouterr().out)

    assert result["recovery"] == "completed_new_report"
    assert result["revision_run_id"] == revised["runs"][-1]["id"]
    assert result["report_dir"] == str(report)
    assert committed == (
        (report / "audit.json").read_bytes(),
        (report / "audit.html").read_bytes(),
    )
    assert not backup.exists()


@pytest.mark.parametrize("failure", ["move", "cleanup"])
def test_interruption_recovery_wraps_io_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    report = tmp_path / "report"
    _write_report(report)
    candidate = tmp_path / ".report.evidentloop-revise-candidate"
    backup = tmp_path / ".report.evidentloop-revise-backup"
    if failure == "move":
        revision_module._copy_report_pair(report, backup)
        (report / "audit.json").unlink()

        def fail_move(*_args):
            raise OSError("forced recovery move failure")

        monkeypatch.setattr("evidentloop.audit.revision.os.replace", fail_move)
    else:
        candidate.mkdir()
        (candidate / "broken").write_text("diagnostic", encoding="utf-8")

        def fail_cleanup(*_args):
            raise OSError("forced recovery cleanup failure")

        monkeypatch.setattr("evidentloop.audit.revision._remove_residual", fail_cleanup)

    with pytest.raises(RevisionError) as captured:
        recover_interrupted_revision(report)

    assert captured.value.code == "revision.recovery_failed"
    assert candidate in captured.value.paths or backup in captured.value.paths


def test_ambiguous_valid_residuals_list_only_recovery_paths(tmp_path: Path) -> None:
    report = tmp_path / "report"
    source, _ = _write_report(report)
    candidate = tmp_path / ".report.evidentloop-revise-candidate"
    _write_report(candidate, source)

    with pytest.raises(RevisionError) as captured:
        recover_interrupted_revision(report)

    assert captured.value.code == "revision.recovery_ambiguous"
    assert captured.value.paths == (report, candidate)
