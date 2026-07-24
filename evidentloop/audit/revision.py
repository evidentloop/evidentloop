"""Deterministic feedback revision and report-pair publication."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Mapping

from evidentloop.renderers.html import render_audit_file, validate_html_trace
from evidentloop.validation import (
    SCHEMA_VERSION,
    AuditValidationError,
    assert_valid_audit,
)
from evidentloop.versions import audit_diff_version, content_version

from .feedback import FeedbackError, normalize_feedback, parse_feedback_jsonl
from .summary import build_summary


NOTICE = "报告已按人工裁定更新；未重新审查代码，模型原判断仍保留。"
_REPORT_FILES = ("audit.json", "audit.html")


class RevisionError(RuntimeError):
    """Stable revision failure with only paths needed for recovery."""

    def __init__(
        self,
        code: str,
        message: str,
        paths: tuple[Path, ...] = (),
    ) -> None:
        self.code = code
        self.message = message
        self.paths = paths
        super().__init__(message)

    def __str__(self) -> str:
        suffix = f"; paths: {', '.join(map(str, self.paths))}" if self.paths else ""
        return f"{self.code}: {self.message}{suffix}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "error",
            "code": self.code,
            "message": self.message,
            "paths": [str(path) for path in self.paths],
        }


def audit_sha256(raw: bytes) -> str:
    return content_version(raw)


def _read_audit(path: Path) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RevisionError(
            "revision.invalid_source", f"cannot read valid audit JSON: {exc}", (path,)
        ) from exc
    if not isinstance(value, dict):
        raise RevisionError(
            "revision.invalid_source", "audit.json must contain an object", (path,)
        )
    if value.get("schema_version") != SCHEMA_VERSION:
        raise RevisionError(
            "revision.unsupported_schema",
            f"current runtime accepts only audit schema {SCHEMA_VERSION}; generate a new report to continue feedback",
            (path,),
        )
    try:
        assert_valid_audit(value)
    except AuditValidationError as exc:
        raise RevisionError("revision.invalid_source", str(exc), (path,)) from exc
    return value, raw


def _report_versions(report_dir: Path) -> dict[str, str | None]:
    audit, raw = _read_audit(report_dir / "audit.json")
    return {
        "diff_version": audit_diff_version(audit),
        "report_version": content_version(raw),
    }


def _report_is_valid(report_dir: Path) -> bool:
    try:
        audit, raw = _read_audit(report_dir / "audit.json")
        html = (report_dir / "audit.html").read_text(encoding="utf-8")
        return not validate_html_trace(
            html, audit, source_audit_sha256=audit_sha256(raw)
        )
    except (OSError, UnicodeError, RevisionError, ValueError):
        return False


def _candidate_path(report_dir: Path) -> Path:
    return report_dir.parent / f".{report_dir.name}.evidentloop-revise-candidate"


def _backup_path(report_dir: Path) -> Path:
    return report_dir.parent / f".{report_dir.name}.evidentloop-revise-backup"


def _report_path_from_audit(source_path: Path) -> Path:
    """Map a formal or deterministic residual audit path to the report path."""
    parent_name = source_path.parent.name
    for suffix in (
        ".evidentloop-revise-candidate",
        ".evidentloop-revise-backup",
    ):
        if parent_name.startswith(".") and parent_name.endswith(suffix):
            report_name = parent_name[1 : -len(suffix)]
            if report_name:
                return source_path.parent.parent / report_name
    return source_path.parent


def _remove_residual(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _copy_report_pair(source: Path, target: Path) -> None:
    """Copy only the managed report pair into a new hidden directory."""
    target.mkdir()
    for name in _REPORT_FILES:
        shutil.copy2(source / name, target / name)


def _replace_report_pair(source: Path, target: Path) -> None:
    """Replace only the managed report pair, leaving sibling files untouched."""
    target.mkdir(parents=True, exist_ok=True)
    for name in _REPORT_FILES:
        os.replace(source / name, target / name)


def _restore_report_pair(report: Path, candidate: Path, backup: Path) -> None:
    """Restore the old pair from a valid backup without moving the report directory."""
    if os.path.lexists(candidate):
        _remove_residual(candidate)
    _copy_report_pair(backup, candidate)
    _replace_report_pair(candidate, report)
    if not _report_is_valid(report):
        raise OSError("restored report pair failed validation")
    _remove_residual(candidate)
    _remove_residual(backup)


def _last_revision_source_hash(report_dir: Path) -> str | None:
    try:
        audit, _ = _read_audit(report_dir / "audit.json")
    except RevisionError:
        return None
    last_run = audit["runs"][-1]
    revision = last_run.get("revision")
    return (
        revision.get("source_audit_sha256") if isinstance(revision, Mapping) else None
    )


def _recover_interrupted_revision(report: Path) -> dict[str, Any]:
    candidate = _candidate_path(report)
    backup = _backup_path(report)
    residuals = [path for path in (candidate, backup) if os.path.lexists(path)]
    if not residuals:
        return {"status": "clean", "report_dir": str(report)}

    report_valid = _report_is_valid(report)
    candidate_valid = _report_is_valid(candidate)
    backup_valid = _report_is_valid(backup)

    if not report_valid and backup_valid:
        _restore_report_pair(report, candidate, backup)
        return {"status": "restored_old_report", "report_dir": str(report)}

    if report_valid:
        removed_invalid = False
        for path, valid in ((candidate, candidate_valid), (backup, backup_valid)):
            if os.path.lexists(path) and not valid:
                _remove_residual(path)
                removed_invalid = True
        if removed_invalid:
            candidate_valid = _report_is_valid(candidate)
            backup_valid = _report_is_valid(backup)

    if report_valid and backup_valid and not os.path.lexists(candidate):
        _, report_raw = _read_audit(report / "audit.json")
        _, backup_raw = _read_audit(backup / "audit.json")
        if _last_revision_source_hash(report) == audit_sha256(backup_raw):
            _remove_residual(backup)
            return {"status": "completed_new_report", "report_dir": str(report)}
        if audit_sha256(report_raw) == audit_sha256(backup_raw):
            _remove_residual(backup)
            return {"status": "restored_old_report", "report_dir": str(report)}

    if report_valid and candidate_valid and not os.path.lexists(backup):
        _, report_raw = _read_audit(report / "audit.json")
        if _last_revision_source_hash(candidate) == audit_sha256(report_raw):
            _remove_residual(candidate)
            return {
                "status": "discarded_uncommitted_candidate",
                "report_dir": str(report),
            }

    if report_valid and candidate_valid and backup_valid:
        _, report_raw = _read_audit(report / "audit.json")
        _, backup_raw = _read_audit(backup / "audit.json")
        report_hash = audit_sha256(report_raw)
        if (
            report_hash == audit_sha256(backup_raw)
            and _last_revision_source_hash(candidate) == report_hash
        ):
            _remove_residual(candidate)
            _remove_residual(backup)
            return {
                "status": "discarded_uncommitted_candidate",
                "report_dir": str(report),
            }

    if report_valid and not os.path.lexists(candidate) and not os.path.lexists(backup):
        return {"status": "discarded_invalid_residuals", "report_dir": str(report)}

    paths = tuple(path for path in (report, candidate, backup) if os.path.lexists(path))
    raise RevisionError(
        "revision.recovery_ambiguous",
        "interrupted revision state is not uniquely recoverable; choose the valid report to keep",
        paths,
    )


def recover_interrupted_revision(report_dir: str | Path) -> dict[str, Any]:
    """Resolve only interruption states whose old/new relationship is provable."""
    requested = Path(report_dir)
    try:
        report = requested.resolve()
    except OSError as exc:
        raise RevisionError(
            "revision.recovery_failed",
            f"cannot resolve report path for recovery: {exc}",
            (requested,),
        ) from exc
    candidate = _candidate_path(report)
    backup = _backup_path(report)
    try:
        return _recover_interrupted_revision(report)
    except RevisionError:
        raise
    except OSError as exc:
        paths = tuple(
            path for path in (report, candidate, backup) if os.path.lexists(path)
        )
        raise RevisionError(
            "revision.recovery_failed",
            f"cannot recover interrupted revision: {exc}",
            paths or (report, candidate, backup),
        ) from exc


def _validate_event_identity(
    audit: Mapping[str, Any],
    events: list[dict[str, Any]],
    source_hash: str,
) -> None:
    latest_run_id = audit["runs"][-1]["id"]
    findings = {
        node["id"]: node for node in audit["nodes"] if node["type"] == "finding"
    }
    for event in events:
        if event["graph_id"] != audit["graph_id"] or event["run_id"] != latest_run_id:
            raise RevisionError(
                "revision.stale_feedback",
                "feedback does not target the current graph and latest run; refresh the report and copy again",
            )
        declared_hash = event.get("source_audit_sha256")
        if declared_hash is not None and declared_hash != source_hash:
            raise RevisionError(
                "revision.stale_feedback",
                "source audit changed after feedback was copied; refresh the report and copy again",
            )
        finding = findings.get(event["target_id"])
        if finding is None or finding["fingerprint"] != event["fingerprint"]:
            raise RevisionError(
                "revision.stale_feedback",
                f"finding identity no longer matches: {event['target_id']}",
            )


def _matching_completed_revision(
    audit: Mapping[str, Any], events: list[dict[str, Any]]
) -> str | None:
    """Return the run id when recovery already committed this exact feedback."""
    latest = audit["runs"][-1]
    revision = latest.get("revision")
    if latest.get("kind") != "feedback_revision" or not isinstance(revision, Mapping):
        return None
    source_hash = revision.get("source_audit_sha256")
    expected_feedback_hash = revision.get("feedback_sha256")
    if not isinstance(source_hash, str) or not isinstance(expected_feedback_hash, str):
        return None
    replay = copy.deepcopy(events)
    for event in replay:
        declared_hash = event.get("source_audit_sha256")
        if declared_hash is not None and declared_hash != source_hash:
            return None
        event.setdefault("source_audit_sha256", source_hash)
    try:
        _, feedback_hash = normalize_feedback(replay)
    except FeedbackError:
        return None
    return str(latest["id"]) if feedback_hash == expected_feedback_hash else None


def _snapshot_summary(summary: Mapping[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(dict(summary))


def _model_summary(source_summary: Mapping[str, Any]) -> tuple[str, str | None]:
    if source_summary.get("basis") == "human_adjudication":
        return str(source_summary["model_verdict"]), source_summary.get(
            "model_overall_severity"
        )
    return str(source_summary["verdict"]), source_summary.get("overall_severity")


def _apply_event(
    finding: dict[str, Any], event: Mapping[str, Any], run_id: str
) -> None:
    model = finding["model_judgment"]
    original_human = copy.deepcopy(finding.get("human_adjudication"))
    original_semantic = (
        finding["status"],
        finding["severity"],
        {
            key: value
            for key, value in (original_human or {}).items()
            if key != "applied_run_id"
        },
    )
    human = dict(original_human or {})
    human.pop("applied_run_id", None)
    action = event["action"]
    if action == "accept":
        finding["status"] = "open"
        human["disposition"] = "accept"
    elif action == "false_positive":
        finding["status"] = "dismissed"
        human["disposition"] = "false_positive"
    elif action == "comment":
        if event["comment"] is None:
            human.pop("comment", None)
        else:
            human["comment"] = event["comment"]
    elif action == "severity_override":
        if event["severity"] is None:
            finding["severity"] = model["severity"]
            human.pop("severity_override", None)
        else:
            finding["severity"] = event["severity"]
            human["severity_override"] = event["severity"]
    current_semantic = (finding["status"], finding["severity"], human)
    if current_semantic == original_semantic:
        if original_human is None:
            finding.pop("human_adjudication", None)
        else:
            finding["human_adjudication"] = original_human
        return
    if human:
        human["applied_run_id"] = run_id
        finding["human_adjudication"] = human
    else:
        finding.pop("human_adjudication", None)


def build_feedback_revision(
    source: Mapping[str, Any],
    events: list[dict[str, Any]],
    *,
    source_hash: str,
) -> dict[str, Any]:
    """Build and fully validate one immutable feedback revision in memory."""
    audit = copy.deepcopy(dict(source))
    source_summary = _snapshot_summary(audit["summary"])
    source_run_id = str(audit["runs"][-1]["id"])
    stored_events = copy.deepcopy(events)
    for event in stored_events:
        event.setdefault("source_audit_sha256", source_hash)
    try:
        stored_events, feedback_hash = normalize_feedback(stored_events)
    except FeedbackError as exc:
        raise RevisionError(exc.code, str(exc)) from exc
    run_digest = hashlib.sha256(f"{source_hash}:{feedback_hash}".encode()).hexdigest()[
        :16
    ]
    run_id = f"run-feedback-{run_digest}"
    if any(run["id"] == run_id for run in audit["runs"]):
        raise RevisionError(
            "revision.duplicate", "this feedback revision already exists"
        )

    findings = {
        node["id"]: node for node in audit["nodes"] if node["type"] == "finding"
    }
    before = {}
    before_effective = {}
    for finding in findings.values():
        before[finding["id"]] = (
            finding["status"],
            finding["severity"],
            copy.deepcopy(finding.get("human_adjudication")),
        )
        before_effective[finding["id"]] = (
            finding["status"],
            finding["severity"],
        )

    for event in stored_events:
        _apply_event(findings[event["target_id"]], event, run_id)
    after = {
        finding_id: (
            finding["status"],
            finding["severity"],
            finding.get("human_adjudication"),
        )
        for finding_id, finding in findings.items()
    }
    if before == after:
        raise RevisionError(
            "revision.no_change", "feedback does not change the current report"
        )

    model_verdict, model_overall_severity = _model_summary(source_summary)
    empty_verdict = (
        "pass_candidate"
        if source_summary["review_status"] == "complete"
        and model_verdict
        in {"pass_candidate", "concerns", "needs_human_triage"}
        else "inconclusive"
    )
    after_effective = {
        finding_id: (finding["status"], finding["severity"])
        for finding_id, finding in findings.items()
    }
    if before_effective == after_effective:
        current = {
            field: source_summary[field]
            for field in (
                "review_status",
                "verdict",
                "overall_severity",
                "finding_count",
                "open_finding_count",
                "fix_count",
                "fix_done_count",
            )
            if field in source_summary
        }
    else:
        current = build_summary(
            findings.values(),
            (node for node in audit["nodes"] if node["type"] == "fix"),
            review_status=str(source_summary["review_status"]),
            empty_verdict=empty_verdict,
            trusted_finding_ids={
                str(edge["from"])
                for edge in audit["edges"]
                if edge["type"] == "finding_in_file"
            },
        )
    current.update(
        {
            "summary_audit_status": source_summary.get(
                "summary_audit_status", "not_audited"
            ),
            "basis": "human_adjudication",
            "model_verdict": model_verdict,
            "model_overall_severity": model_overall_severity,
            "notice": NOTICE,
        }
    )
    if "extensions" in source_summary:
        current["extensions"] = copy.deepcopy(source_summary["extensions"])

    revision_run = {
        "id": run_id,
        "label": f"反馈修订 {sum(run.get('kind') == 'feedback_revision' for run in audit['runs']) + 1}",
        "status": current["verdict"],
        "summary": NOTICE,
        "kind": "feedback_revision",
        "revision": {
            "source_run_id": source_run_id,
            "source_audit_sha256": source_hash,
            "feedback_sha256": feedback_hash,
            "source_summary": source_summary,
            "events": stored_events,
            "notice": NOTICE,
        },
    }
    audit["runs"].append(revision_run)
    audit["edges"].append(
        {
            "id": f"edge-{run_id}-supersedes",
            "type": "supersedes_run",
            "from": run_id,
            "to": source_run_id,
        }
    )
    audit["summary"] = current
    try:
        assert_valid_audit(audit)
    except AuditValidationError as exc:
        raise RevisionError("revision.invalid_candidate", str(exc)) from exc
    return audit


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    descriptor, temp_name = tempfile.mkstemp(
        prefix=".audit.json.", suffix=".tmp", dir=path.parent
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _generate_report(report_dir: Path, audit: Mapping[str, Any]) -> None:
    try:
        os.mkdir(report_dir, 0o700)
        _write_json(report_dir / "audit.json", audit)
        render_audit_file(report_dir / "audit.json", report_dir / "audit.html")
    except Exception as exc:
        raise RevisionError(
            "revision.candidate_failed",
            f"cannot generate a valid report pair: {exc}",
            (report_dir,),
        ) from exc
    if not _report_is_valid(report_dir):
        raise RevisionError(
            "revision.candidate_failed",
            "generated report pair failed validation",
            (report_dir,),
        )


def _commit_in_place(
    report: Path, candidate: Path, backup: Path, source_hash: str
) -> None:
    _, current_raw = _read_audit(report / "audit.json")
    if audit_sha256(current_raw) != source_hash:
        _remove_residual(candidate)
        raise RevisionError(
            "revision.stale_source",
            "source audit changed before commit; refresh the report and copy again",
            (report,),
        )
    try:
        _copy_report_pair(report, backup)
        if not _report_is_valid(backup):
            raise OSError("backup report pair failed validation")
    except Exception as exc:
        if os.path.lexists(backup):
            _remove_residual(backup)
        raise RevisionError(
            "revision.commit_failed",
            f"could not create a valid report backup: {exc}",
            tuple(path for path in (report, candidate) if os.path.lexists(path)),
        ) from exc
    try:
        _replace_report_pair(candidate, report)
        if not _report_is_valid(report):
            raise RevisionError(
                "revision.commit_invalid", "committed report pair failed validation"
            )
    except Exception as exc:
        try:
            _restore_report_pair(report, candidate, backup)
        except Exception as rollback_exc:
            raise RevisionError(
                "revision.rollback_failed",
                f"commit failed and automatic rollback was incomplete: {rollback_exc}",
                tuple(
                    path
                    for path in (report, candidate, backup)
                    if os.path.lexists(path)
                ),
            ) from exc
        if isinstance(exc, RevisionError):
            raise exc
        raise RevisionError(
            "revision.commit_failed",
            f"commit failed; old report restored: {exc}",
            tuple(path for path in (report, candidate) if os.path.lexists(path)),
        ) from exc
    try:
        _remove_residual(candidate)
        _remove_residual(backup)
    except OSError:
        # A valid new pair is already committed; recovery can prove and clean the residual.
        pass


def _revise_audit(
    source_audit_json: str | Path,
    feedback_jsonl: str | Path,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Apply feedback to one explicit source report and publish the new pair."""
    source_path = Path(source_audit_json).resolve()
    if source_path.name != "audit.json":
        raise RevisionError(
            "revision.invalid_source_path",
            "source must be the report's audit.json",
            (source_path,),
        )
    report = _report_path_from_audit(source_path)
    source_path = report / "audit.json"
    recovery = recover_interrupted_revision(report)
    source, source_raw = _read_audit(source_path)
    if not _report_is_valid(report):
        raise RevisionError(
            "revision.invalid_source_pair",
            "source audit.json and audit.html are not a valid pair",
            (report,),
        )
    source_hash = audit_sha256(source_raw)
    try:
        feedback_raw = Path(feedback_jsonl).read_bytes()
        parsed = parse_feedback_jsonl(feedback_raw)
    except OSError as exc:
        raise RevisionError(
            "revision.invalid_feedback",
            f"cannot read feedback: {exc}",
            (Path(feedback_jsonl),),
        ) from exc
    except FeedbackError as exc:
        message = (
            f"line {exc.line}: {exc.message}" if exc.line is not None else exc.message
        )
        raise RevisionError(exc.code, message) from exc
    if recovery["status"] == "completed_new_report" and out_dir is None:
        revision_run_id = _matching_completed_revision(source, parsed)
        if revision_run_id is not None:
            return {
                "status": "ok",
                "mode": "in_place",
                "report_dir": str(report),
                "audit_json": str(source_path),
                "audit_html": str(report / "audit.html"),
                "schema_version": SCHEMA_VERSION,
                "revision_run_id": revision_run_id,
                "recovery": recovery["status"],
                **_report_versions(report),
            }
    _validate_event_identity(source, parsed, source_hash)
    candidate_audit = build_feedback_revision(
        source,
        parsed,
        source_hash=source_hash,
    )

    if out_dir is not None:
        target = Path(out_dir).resolve()
        reserved = (_candidate_path(report), _backup_path(report))
        if target in reserved:
            raise RevisionError(
                "revision.invalid_output_path",
                "output directory is reserved for EvidentLoop recovery; choose another directory",
                (report, target),
            )
        try:
            target.relative_to(report)
        except ValueError:
            pass
        else:
            raise RevisionError(
                "revision.invalid_output_path",
                "output directory must not be inside the source report directory",
                (report, target),
            )
        staging = target.parent / f".{target.name}.evidentloop-staging"
        if os.path.lexists(target) or os.path.lexists(staging):
            raise RevisionError(
                "revision.output_exists",
                "output or staging path already exists",
                (target, staging),
            )
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise RevisionError(
                "revision.output_parent_failed",
                f"cannot create output parent: {exc}",
                (target.parent, target),
            ) from exc
        _generate_report(staging, candidate_audit)
        _, current_raw = _read_audit(source_path)
        if audit_sha256(current_raw) != source_hash:
            _remove_residual(staging)
            raise RevisionError(
                "revision.stale_source",
                "source audit changed before commit; refresh the report and copy again",
                (report,),
            )
        try:
            os.replace(staging, target)
        except OSError as exc:
            raise RevisionError(
                "revision.commit_failed", str(exc), (staging, target)
            ) from exc
        if not _report_is_valid(target):
            try:
                os.replace(target, staging)
            except OSError as exc:
                raise RevisionError(
                    "revision.rollback_failed",
                    f"published copy failed validation and could not be moved back: {exc}",
                    tuple(path for path in (target, staging) if os.path.lexists(path)),
                ) from exc
            raise RevisionError(
                "revision.commit_invalid",
                "published copy failed validation",
                (staging,),
            )
        return {
            "status": "ok",
            "mode": "copy",
            "report_dir": str(target),
            "audit_json": str(target / "audit.json"),
            "audit_html": str(target / "audit.html"),
            "schema_version": SCHEMA_VERSION,
            "revision_run_id": candidate_audit["runs"][-1]["id"],
            "recovery": recovery["status"],
            **_report_versions(target),
        }

    candidate = _candidate_path(report)
    backup = _backup_path(report)
    if os.path.lexists(candidate) or os.path.lexists(backup):
        raise RevisionError(
            "revision.residual_exists",
            "revision residuals remain after recovery",
            (candidate, backup),
        )
    _generate_report(candidate, candidate_audit)
    _commit_in_place(report, candidate, backup, source_hash)
    return {
        "status": "ok",
        "mode": "in_place",
        "report_dir": str(report),
        "audit_json": str(report / "audit.json"),
        "audit_html": str(report / "audit.html"),
        "schema_version": SCHEMA_VERSION,
        "revision_run_id": candidate_audit["runs"][-1]["id"],
        "recovery": recovery["status"],
        **_report_versions(report),
    }


def revise_audit(
    source_audit_json: str | Path,
    feedback_jsonl: str | Path,
    out_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Apply feedback while keeping all public I/O failures structured."""
    source = Path(source_audit_json)
    report = source.parent
    related = [
        source,
        Path(feedback_jsonl),
        _candidate_path(report),
        _backup_path(report),
    ]
    if out_dir is not None:
        target = Path(out_dir)
        related.extend([target, target.parent / f".{target.name}.evidentloop-staging"])
    try:
        return _revise_audit(source, feedback_jsonl, out_dir)
    except RevisionError:
        raise
    except OSError as exc:
        paths = tuple(path for path in related if os.path.lexists(path))
        raise RevisionError(
            "revision.io_failed",
            f"report update failed during local I/O: {exc}",
            paths or tuple(related[:2]),
        ) from exc
