"""Finalize completion gates, publication and failure-boundary tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from change_audit.audit.finalize import AuditWorkflowError, finalize_review, prepare_local_diff
from change_audit.cli import main
from change_audit.renderers.html import AuditRenderError
from change_audit.validation import AuditValidationError, ValidationIssue, assert_valid_audit
from tests.git_helpers import initialized_repo, stage_simple_change


def _prepare(tmp_path: Path, *, name: str = "report") -> dict[str, str]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    repo = initialized_repo(tmp_path)
    stage_simple_change(repo)
    return prepare_local_diff(repo, "staged", repo / "reports" / name)


def _header(locator: dict[str, str]) -> str:
    run_dir = Path(locator["staging_dir"]) / ".run"
    index = json.loads((run_dir / "hunk-index.json").read_text(encoding="utf-8"))
    return index["hunks"][0]["header"]


def _analysis(
    locator: dict[str, str],
    *,
    category: str = "logic_error",
    where: str | None = None,
    overall: bool = True,
    overall_text: str = "The diff has one concrete problem.",
    title: str = "Updated value breaks the documented runtime behavior.",
) -> str:
    location = where or f"`app.py`, line 1, {_header(locator)}"
    ending = (
        f"\n## Section 3: Overall Assessment\n\n{overall_text}\n"
        if overall
        else ""
    )
    return f"""\
<!-- change-audit-run-id: {locator['run_id']} -->
## Section 1: Findings

**f-001**
- **Where**: {location}
- **What**: {title}
- **Why**: Consumers require the previous value and now receive an incompatible result.
- **Severity estimate**: HIGH
- **Category**: {category}

## Section 2: Observations

None.
{ending}"""


def _write_raw(locator: dict[str, str], value: str) -> None:
    Path(locator["raw_analysis_path"]).write_text(value, encoding="utf-8")


def _audit(locator: dict[str, str]) -> dict:
    return json.loads((Path(locator["final_dir"]) / "audit.json").read_text(encoding="utf-8"))


def test_finalize_publishes_exact_bug_pair_and_cleans_run_dir(tmp_path: Path) -> None:
    locator = _prepare(tmp_path)
    trusted_header = _header(locator)
    _write_raw(locator, _analysis(locator))

    result = finalize_review(locator["final_dir"])

    final_dir = Path(locator["final_dir"])
    assert result["review_status"] == "complete"
    assert result["verdict"] == "concerns"
    assert final_dir.is_dir()
    assert {item.name for item in final_dir.iterdir()} == {"audit.json", "audit.html"}
    assert not Path(locator["staging_dir"]).exists()
    audit = _audit(locator)
    finding = next(item for item in audit["nodes"] if item["type"] == "finding")
    assert finding["category"] == "bug"
    assert finding["hunk"].startswith(trusted_header)
    assert audit["runs"][0]["summary"] == "The diff has one concrete problem."
    assert audit["extensions"]["change_audit"]["reviewer_prompt"]["version"] == "v0.2"
    assert audit["extensions"]["change_audit"]["reviewer_prompt"]["sha256"].startswith(
        "sha256:"
    )
    assert_valid_audit(audit)
    html = (final_dir / "audit.html").read_text(encoding="utf-8")
    assert f'data-graph-id="{audit["graph_id"]}"' in html
    assert f'data-run-id="{locator["run_id"]}"' in html
    assert "The diff has one concrete problem." in html


def test_finalize_distinguishes_clean_partial_failed_and_unanchored(tmp_path: Path) -> None:
    clean = _prepare(tmp_path / "clean")
    _write_raw(
        clean,
        f"<!-- change-audit-run-id: {clean['run_id']} -->\n"
        "## Section 1: Findings\n\n未发现问题。\n\n"
        "## Section 3: Overall Assessment\n\nThe diff is clean.\n",
    )
    clean_result = finalize_review(clean["final_dir"])
    assert clean_result["review_status"] == "complete"
    assert clean_result["verdict"] == "inconclusive"
    assert _audit(clean)["summary"]["risk_score"] is None
    assert "findings-section" not in (Path(clean["final_dir"]) / "audit.html").read_text()

    partial = _prepare(tmp_path / "partial")
    _write_raw(partial, _analysis(partial, overall=False))
    partial_result = finalize_review(partial["final_dir"])
    partial_summary = _audit(partial)["summary"]
    assert partial_result["review_status"] == "partial"
    assert partial_summary["verdict"] == "inconclusive"
    assert partial_summary["risk_score"] is None
    assert partial_summary["finding_count"] == 1

    empty_overall = _prepare(tmp_path / "empty-overall")
    _write_raw(empty_overall, _analysis(empty_overall, overall_text=""))
    empty_overall_result = finalize_review(empty_overall["final_dir"])
    assert empty_overall_result["review_status"] == "partial"
    assert _audit(empty_overall)["runs"][0]["summary"].startswith("宿主审查生成")

    failed = _prepare(tmp_path / "failed")
    _write_raw(
        failed,
        f"<!-- change-audit-run-id: {failed['run_id']} -->\nI cannot comply with this review.",
    )
    failed_result = finalize_review(failed["final_dir"])
    assert failed_result["review_status"] == "failed"
    assert failed_result["verdict"] == "inconclusive"
    assert (Path(failed["final_dir"]) / ".run" / "review-result.json").is_file()

    unanchored = _prepare(tmp_path / "unanchored")
    _write_raw(
        unanchored,
        _analysis(unanchored, where="`app.py`, line 999, @@ -900 +900 @@"),
    )
    unanchored_result = finalize_review(unanchored["final_dir"])
    unanchored_summary = _audit(unanchored)["summary"]
    assert unanchored_result["verdict"] == "needs_human_triage"
    assert unanchored_summary["risk_score"] is None
    assert unanchored_summary["unscored_finding_count"] == 1

    malformed = _prepare(tmp_path / "malformed-finding")
    _write_raw(
        malformed,
        f"<!-- change-audit-run-id: {malformed['run_id']} -->\n"
        "## Section 1: Findings\n\n"
        "### f-001\n"
        "- **Where**: `app.py`, line 1\n"
        "- **What**: Missing required fields.\n\n"
        "## Section 3: Overall Assessment\n\n输出不完整。\n",
    )
    malformed_result = finalize_review(malformed["final_dir"])
    assert malformed_result["review_status"] == "partial"
    assert malformed_result["verdict"] == "inconclusive"


def test_mixed_valid_and_malformed_finding_ids_cannot_finalize_as_complete(
    tmp_path: Path,
) -> None:
    locator = _prepare(tmp_path)
    valid = _analysis(locator).replace(
        "## Section 2: Observations",
        "### f-2\n"
        "- **Where**: `app.py`, line 1\n"
        "- **What**: 非法编号的 finding 不得被静默丢弃。\n"
        "- **Why**: 协议要求三位数字编号。\n"
        "- **Severity estimate**: LOW\n"
        "- **Category**: other\n\n"
        "## Section 2: Observations",
    )
    _write_raw(locator, valid)

    result = finalize_review(locator["final_dir"])

    assert result["review_status"] == "partial"
    assert result["verdict"] == "inconclusive"
    assert _audit(locator)["summary"]["finding_count"] == 1


def test_finalize_keep_artifacts_and_escape_malicious_analysis(tmp_path: Path) -> None:
    locator = _prepare(tmp_path)
    attack = '</script><script data-attack="1">alert(1)</script>'
    _write_raw(locator, _analysis(locator, title=attack, overall_text=attack))
    finalize_review(locator["final_dir"], keep_review_artifacts=True)
    final_dir = Path(locator["final_dir"])
    assert (final_dir / ".run" / "review-result.json").is_file()
    html = (final_dir / "audit.html").read_text(encoding="utf-8")
    assert attack not in html
    assert "&lt;/script&gt;" in html
    assert 'data-attack="1"' not in html


def test_finalize_rejects_tampered_prompt_provenance(tmp_path: Path) -> None:
    locator = _prepare(tmp_path)
    _write_raw(locator, _analysis(locator))
    prompt_path = Path(locator["prompt_path"])
    prompt_path.write_text(prompt_path.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8")

    with pytest.raises(AuditWorkflowError, match="prompt fingerprint mismatch"):
        finalize_review(locator["final_dir"])

    assert not Path(locator["final_dir"]).exists()
    assert Path(locator["staging_dir"]).is_dir()


@pytest.mark.parametrize("failure", ["missing_raw", "run_mismatch"])
def test_identity_and_missing_material_fail_without_formal_output(
    tmp_path: Path,
    failure: str,
) -> None:
    locator = _prepare(tmp_path)
    if failure == "run_mismatch":
        _write_raw(locator, _analysis(locator).replace(locator["run_id"], "run-other", 1))
    with pytest.raises(AuditWorkflowError):
        finalize_review(locator["final_dir"])
    assert not Path(locator["final_dir"]).exists()
    assert Path(locator["staging_dir"]).is_dir()
    assert not (Path(locator["staging_dir"]) / "audit.html").exists()


@pytest.mark.parametrize("target_kind", ["directory", "dangling_symlink"])
def test_target_appearing_after_prepare_is_preserved_and_not_success(
    tmp_path: Path,
    target_kind: str,
) -> None:
    locator = _prepare(tmp_path)
    _write_raw(locator, _analysis(locator))
    final_dir = Path(locator["final_dir"])
    if target_kind == "directory":
        final_dir.mkdir()
        (final_dir / "owner.txt").write_text("existing", encoding="utf-8")
    else:
        final_dir.symlink_to(final_dir.parent / "missing", target_is_directory=True)

    with pytest.raises(AuditWorkflowError, match="already exists"):
        finalize_review(final_dir)
    assert Path(locator["staging_dir"]).is_dir()
    if target_kind == "directory":
        assert (final_dir / "owner.txt").read_text() == "existing"
    else:
        assert final_dir.is_symlink()


def test_json_render_trace_and_rename_failures_preserve_staging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = _prepare(tmp_path / "invalid")
    _write_raw(invalid, _analysis(invalid))
    monkeypatch.setattr(
        "change_audit.audit.finalize.assert_valid_audit",
        lambda audit: (_ for _ in ()).throw(
            AuditValidationError([ValidationIssue("forced", "/", "forced")])
        ),
    )
    with pytest.raises(AuditWorkflowError, match="validation failed"):
        finalize_review(invalid["final_dir"])
    assert not Path(invalid["final_dir"]).exists()
    assert Path(invalid["staging_dir"]).is_dir()
    monkeypatch.undo()

    render = _prepare(tmp_path / "render")
    _write_raw(render, _analysis(render))
    monkeypatch.setattr(
        "change_audit.audit.finalize.render_audit_file",
        lambda source, target: (_ for _ in ()).throw(AuditRenderError("forced render")),
    )
    with pytest.raises(AuditWorkflowError, match="forced render"):
        finalize_review(render["final_dir"])
    assert not Path(render["final_dir"]).exists()
    assert (Path(render["staging_dir"]) / "audit.json").is_file()
    monkeypatch.undo()

    trace = _prepare(tmp_path / "trace")
    _write_raw(trace, _analysis(trace))
    monkeypatch.setattr(
        "change_audit.renderers.html.validate_html_trace",
        lambda html, audit: ["forced trace"],
    )
    with pytest.raises(AuditWorkflowError, match="forced trace"):
        finalize_review(trace["final_dir"])
    assert not Path(trace["final_dir"]).exists()
    assert Path(trace["staging_dir"]).is_dir()
    monkeypatch.undo()

    rename = _prepare(tmp_path / "rename")
    _write_raw(rename, _analysis(rename))
    monkeypatch.setattr(
        "change_audit.audit.finalize.os.rename",
        lambda source, target: (_ for _ in ()).throw(OSError("forced rename")),
    )
    with pytest.raises(AuditWorkflowError, match="forced rename"):
        finalize_review(rename["final_dir"])
    assert not Path(rename["final_dir"]).exists()
    staging = Path(rename["staging_dir"])
    assert (staging / "audit.json").is_file()
    assert (staging / "audit.html").is_file()
    assert (staging / ".run" / "finalize-error.json").is_file()


def test_finalize_cli_stdout_is_only_result_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    locator = _prepare(tmp_path)
    _write_raw(locator, _analysis(locator))
    assert main(["finalize", "--out", locator["final_dir"]]) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert set(result) >= {"run_id", "audit_json", "audit_html", "review_status", "verdict"}
    assert captured.err == ""
