"""Prepare/finalize workflow for host-orchestrated code-diff reviews."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Mapping

from evidentloop.adapters.gitdiff import GitDiffCollectionError, collect_git_diff
from evidentloop.renderers.html import AuditRenderError, render_audit_file
from evidentloop.review.core.prompt import (
    PRODUCT_REVIEWER_PROMPT_SOURCE,
    PRODUCT_REVIEWER_PROMPT_VERSION,
    render_host_reviewer_prompt,
)
from evidentloop.review.ingest import run_ingest
from evidentloop.review.normalizer import declared_finding_ids
from evidentloop.review.pack import assemble_pack, pack_to_json
from evidentloop.review.schema import (
    BudgetStatus,
    ReviewStatus,
    ReviewerFailureReason,
    review_pack_from_dict,
    to_serializable,
)
from evidentloop.validation import AuditValidationError, assert_valid_audit
from evidentloop.versions import audit_diff_version, content_version

from .adapter import build_audit_graph


class AuditWorkflowError(RuntimeError):
    """A hard workflow failure that must not publish a formal report."""

    def __init__(self, message: str, *, staging_dir: Path | None = None) -> None:
        self.staging_dir = staging_dir
        suffix = f"; staging preserved at {staging_dir}" if staging_dir else ""
        super().__init__(message + suffix)


_RUN_ID_RE = re.compile(r"(?m)^<!-- evidentloop-run-id: ([^\s]+) -->\s*$")
_FINDINGS_SECTION_RE = re.compile(
    r"(?ms)^#+\s*Section 1:\s*Findings\s*(.*?)(?:^#+\s*Section 2:|^#+\s*Section 3:|\Z)",
    re.IGNORECASE,
)
_OVERALL_RE = re.compile(r"(?m)^#+\s*Section 3:\s*Overall Assessment\s*$", re.IGNORECASE)
_OVERALL_SECTION_RE = re.compile(
    r"(?ms)^#+\s*Section 3:\s*Overall Assessment\s*\n+(.*?)(?=^#+\s*Section\s+\d+:|\Z)",
    re.IGNORECASE,
)
_EXPLICIT_ZERO_RE = re.compile(
    r"\b(no findings|no issues(?:\s+found)?|zero findings|nothing to report)\b"
    r"|未发现(?:任何)?(?:问题|缺陷)|没有发现(?:任何)?(?:问题|缺陷)",
    re.IGNORECASE,
)
_REFUSAL_RE = re.compile(
    r"\b(i cannot comply|i can(?:no|')t review|unable to review|refuse to review)\b",
    re.IGNORECASE,
)


def _lexists(path: Path) -> bool:
    return os.path.lexists(os.fspath(path))


def _best_effort_chmod(path: Path, mode: int) -> None:
    try:
        path.chmod(mode)
    except (NotImplementedError, OSError):
        pass


def _atomic_write_text(path: Path, value: str, *, mode: int = 0o600) -> None:
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        try:
            os.fchmod(descriptor, mode)
        except (AttributeError, NotImplementedError, OSError):
            pass
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        _best_effort_chmod(path, mode)
    except Exception:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuditWorkflowError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AuditWorkflowError(f"expected a JSON object in {path}")
    return value


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return (cleaned or "local-diff")[:48]


def _repository_display_name(repo_root: Path) -> str:
    """Build a readable report name without exposing the selected revision range."""
    parts = [part for part in re.split(r"[-_.\s]+", repo_root.name) if part]
    rendered = [part.capitalize() if part.islower() else part for part in parts]
    return " ".join(rendered) or "Local Repository"


def _staging_path(final_dir: Path) -> Path:
    return final_dir.parent / f".{final_dir.name}.evidentloop-staging"


def _resolve_leaf(path: Path, *, base: Path | None = None) -> Path:
    """Resolve a path's parent while preserving the final leaf identity."""
    candidate = path if path.is_absolute() else (base or Path.cwd()) / path
    return candidate.parent.resolve() / candidate.name


def _candidate_available(final_dir: Path) -> bool:
    return not _lexists(final_dir) and not _lexists(_staging_path(final_dir))


def _select_output(repo_root: Path, diff_spec: str, output_dir: str | Path | None) -> Path:
    if output_dir is not None:
        requested = Path(output_dir)
        final_dir = _resolve_leaf(requested, base=repo_root)
        if not _candidate_available(final_dir):
            raise AuditWorkflowError(
                f"output or staging leaf already exists: {final_dir}"
            )
        return final_dir

    parent = repo_root / "audit"
    base = f"{dt.datetime.now().strftime('%Y%m%d')}_{_slug(diff_spec)}"
    for suffix in range(1, 10_000):
        name = base if suffix == 1 else f"{base}-{suffix}"
        candidate = parent / name
        if _candidate_available(candidate):
            return candidate.resolve()
    raise AuditWorkflowError("cannot allocate an unused default audit directory")


def _file_nodes(bundle: Any) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for index, item in enumerate(bundle.files, start=1):
        node: dict[str, Any] = {
            "id": f"file-{index:03d}",
            "type": "file",
            "path": item.path,
            "change_type": item.change_type,
            "additions": item.additions,
            "deletions": item.deletions,
        }
        if item.old_path and item.new_path and item.old_path != item.new_path:
            node["extensions"] = {
                "evidentloop": {"old_path": item.old_path, "new_path": item.new_path}
            }
        nodes.append(node)
    return nodes


def _prepare_local_diff(
    repo_path: str | Path,
    diff_spec: str,
    output_dir: str | Path | None = None,
    *,
    source_extensions: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Prepare a hidden review workspace and return its machine locator."""
    repo_root = Path(repo_path).resolve()
    try:
        bundle = collect_git_diff(repo_root, diff_spec)
    except GitDiffCollectionError as exc:
        raise AuditWorkflowError(str(exc)) from exc

    final_dir = _select_output(repo_root, diff_spec, output_dir)
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = _staging_path(final_dir)
    if _lexists(final_dir) or _lexists(staging_dir):
        raise AuditWorkflowError(f"output or staging leaf already exists: {final_dir}")
    try:
        os.mkdir(staging_dir, 0o700)
    except OSError as exc:
        raise AuditWorkflowError(f"cannot exclusively create staging directory: {exc}") from exc
    _best_effort_chmod(staging_dir, 0o700)
    run_dir = staging_dir / ".run"
    try:
        os.mkdir(run_dir, 0o700)
        _best_effort_chmod(run_dir, 0o700)
    except OSError as exc:
        raise AuditWorkflowError(
            f"cannot create review workspace: {exc}", staging_dir=staging_dir
        ) from exc

    run_id = f"run-{uuid.uuid4().hex}"
    graph_id = f"audit:{run_id}"
    files = _file_nodes(bundle)
    repository_name = _repository_display_name(repo_root)
    additions = sum(item.additions for item in bundle.files)
    deletions = sum(item.deletions for item in bundle.files)
    binary_files = sum(1 for item in bundle.files if item.binary)
    binary_suffix = f"，其中 {binary_files} 个二进制文件" if binary_files else ""
    pack = assemble_pack(
        bundle.diff,
        changed_files=bundle.changed_files,
        intent=f"Audit Git diff {diff_spec}",
        diff_source=bundle.diff_source,
    )
    try:
        try:
            prompt, boundary = render_host_reviewer_prompt(pack, run_id=run_id)
        except ValueError as exc:
            raise AuditWorkflowError(str(exc)) from exc
    except AuditWorkflowError as exc:
        raise AuditWorkflowError(str(exc), staging_dir=staging_dir) from exc
    locator = {
        "schema_version": "1",
        "run_id": run_id,
        "final_dir": str(final_dir),
        "staging_dir": str(staging_dir),
        "prompt_path": str(run_dir / "prompt.md"),
        "raw_analysis_path": str(run_dir / "raw-analysis.md"),
    }
    source: dict[str, Any] = {
        "type": "git_diff",
        "ref": diff_spec,
        "description": f"{repository_name} 本地 Git diff 审计",
    }
    if source_extensions:
        source["extensions"] = dict(source_extensions)
    skeleton = {
        "schema_version": "1",
        "run_id": run_id,
        "graph_id": graph_id,
        "repo_root": str(repo_root),
        "diff_spec": diff_spec,
        "artifact_fingerprint": pack.artifact_fingerprint,
        "pack_fingerprint": pack.pack_fingerprint,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "final_dir": str(final_dir),
        "staging_dir": str(staging_dir),
        "prompt_boundary": boundary,
        "reviewer_prompt": {
            "source": PRODUCT_REVIEWER_PROMPT_SOURCE,
            "version": PRODUCT_REVIEWER_PROMPT_VERSION,
            "sha256": _sha256_text(prompt),
        },
        "source": source,
        "run": {
            "id": run_id,
            "label": f"{repository_name} 代码变更审计",
            "status": "inconclusive",
            "summary": "Host review has not been finalized.",
        },
        "change": {
            "id": "change-001",
            "type": "change",
            "title": f"{repository_name} 变更",
            "summary": (
                f"共 {len(files)} 个文件发生变更（+{additions}/-{deletions}{binary_suffix}）。"
            ),
        },
        "files": files,
    }
    hunk_index = bundle.hunk_index_dict(
        run_id=run_id,
        artifact_fingerprint=pack.artifact_fingerprint,
    )
    try:
        _atomic_write_json(run_dir / "locator.json", locator)
        _atomic_write_json(run_dir / "audit-skeleton.json", skeleton)
        _atomic_write_text(run_dir / "review-pack.json", pack_to_json(pack) + "\n")
        _atomic_write_json(run_dir / "hunk-index.json", hunk_index)
        _atomic_write_text(run_dir / "prompt.md", prompt)
    except Exception as exc:
        raise AuditWorkflowError(
            f"cannot write review workspace: {exc}", staging_dir=staging_dir
        ) from exc
    return locator


def prepare_local_diff(
    repo_path: str | Path,
    diff_spec: str,
    output_dir: str | Path | None = None,
) -> dict[str, str]:
    """Prepare a normal host-reviewed Git diff without synthetic provenance."""
    return _prepare_local_diff(repo_path, diff_spec, output_dir)


def _completion_state(raw_analysis: str) -> str:
    body = _RUN_ID_RE.sub("", raw_analysis, count=1).strip()
    findings_match = _FINDINGS_SECTION_RE.search(body)
    if not body or (_REFUSAL_RE.search(body) and findings_match is None):
        return "failed"
    if (
        findings_match is None
        or _OVERALL_RE.search(body) is None
        or _overall_assessment(body) is None
    ):
        return "partial" if re.search(r"(?m)^#+\s*Section\s+\d+:", body) else "failed"
    findings_body = findings_match.group(1)
    if not (declared_finding_ids(body) or _EXPLICIT_ZERO_RE.search(findings_body)):
        return "partial"
    return "complete"


def _overall_assessment(raw_analysis: str) -> str | None:
    """Extract reviewer prose for display after the completion gate has passed."""
    match = _OVERALL_SECTION_RE.search(raw_analysis)
    if match is None:
        return None
    value = re.sub(r"\s+", " ", match.group(1)).strip()
    return value or None


def _validate_run_identity(raw_analysis: str, expected_run_id: str) -> None:
    identities = _RUN_ID_RE.findall(raw_analysis)
    if identities != [expected_run_id]:
        raise AuditWorkflowError(
            "raw analysis must contain exactly one matching evidentloop run identity"
        )


def _record_finalize_failure(staging_dir: Path, message: str) -> None:
    try:
        run_dir = staging_dir / ".run"
        run_dir.mkdir(mode=0o700, exist_ok=True)
        _best_effort_chmod(run_dir, 0o700)
        _atomic_write_json(
            run_dir / "finalize-error.json",
            {"error": message, "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat()},
        )
    except Exception:
        pass


def finalize_review(
    output_dir: str | Path,
    keep_review_artifacts: bool = False,
) -> dict[str, Any]:
    """Finalize one prepared host review and atomically publish its artifact pair."""
    final_dir = _resolve_leaf(Path(output_dir))
    staging_dir = _staging_path(final_dir)
    if _lexists(final_dir):
        raise AuditWorkflowError(f"final output leaf already exists: {final_dir}")
    if not staging_dir.is_dir() or staging_dir.is_symlink():
        raise AuditWorkflowError(f"prepared staging directory is missing or unsafe: {staging_dir}")
    run_dir = staging_dir / ".run"
    if not run_dir.is_dir() or run_dir.is_symlink():
        raise AuditWorkflowError("prepared .run directory is missing or unsafe", staging_dir=staging_dir)

    try:
        locator = _read_json_object(run_dir / "locator.json")
        skeleton = _read_json_object(run_dir / "audit-skeleton.json")
        hunk_index = _read_json_object(run_dir / "hunk-index.json")
        pack_data = _read_json_object(run_dir / "review-pack.json")
        prompt_text = (run_dir / "prompt.md").read_text(encoding="utf-8")
        raw_analysis = (run_dir / "raw-analysis.md").read_text(encoding="utf-8")
    except AuditWorkflowError as exc:
        raise AuditWorkflowError(str(exc), staging_dir=staging_dir) from exc
    except (OSError, UnicodeError) as exc:
        raise AuditWorkflowError(
            f"cannot read prepared review material: {exc}", staging_dir=staging_dir
        ) from exc

    run_id = str(locator.get("run_id") or "")
    identity_values = {
        run_id,
        str(skeleton.get("run_id") or ""),
        str(hunk_index.get("run_id") or ""),
    }
    if len(identity_values) != 1 or not run_id:
        raise AuditWorkflowError("locator, skeleton and hunk index run_id mismatch", staging_dir=staging_dir)
    if locator.get("final_dir") != str(final_dir) or locator.get("staging_dir") != str(staging_dir):
        raise AuditWorkflowError("locator paths do not match the requested output", staging_dir=staging_dir)
    if skeleton.get("final_dir") != str(final_dir) or skeleton.get("staging_dir") != str(staging_dir):
        raise AuditWorkflowError("skeleton paths do not match the requested output", staging_dir=staging_dir)
    if skeleton.get("artifact_fingerprint") != hunk_index.get("artifact_fingerprint"):
        raise AuditWorkflowError("prepared artifact fingerprint mismatch", staging_dir=staging_dir)
    prompt_contract = skeleton.get("reviewer_prompt")
    if not isinstance(prompt_contract, Mapping):
        raise AuditWorkflowError("skeleton reviewer prompt contract is missing", staging_dir=staging_dir)
    prompt_source = str(prompt_contract.get("source") or "")
    prompt_version = str(prompt_contract.get("version") or "")
    prompt_sha256 = str(prompt_contract.get("sha256") or "")
    if (
        prompt_source != PRODUCT_REVIEWER_PROMPT_SOURCE
        or prompt_version != PRODUCT_REVIEWER_PROMPT_VERSION
    ):
        raise AuditWorkflowError("prepared reviewer prompt version mismatch", staging_dir=staging_dir)
    # prepare/finalize may run in separate host processes. The frozen hash keeps
    # the reported prompt provenance tied to the exact reviewed payload.
    if prompt_sha256 != _sha256_text(prompt_text):
        raise AuditWorkflowError("prepared reviewer prompt fingerprint mismatch", staging_dir=staging_dir)
    try:
        _validate_run_identity(raw_analysis, run_id)
    except AuditWorkflowError as exc:
        raise AuditWorkflowError(str(exc), staging_dir=staging_dir) from exc

    try:
        pack = review_pack_from_dict(pack_data)
        if pack.artifact_fingerprint != skeleton.get("artifact_fingerprint"):
            raise AuditWorkflowError("ReviewPack artifact fingerprint mismatch")
        if pack.pack_fingerprint != skeleton.get("pack_fingerprint"):
            raise AuditWorkflowError("ReviewPack fingerprint mismatch")
        completion = _completion_state(raw_analysis)
        result = run_ingest(
            pack,
            raw_analysis,
            model="host-llm",
            prompt_source=prompt_source,
            prompt_version=prompt_version,
        )
        if completion == "partial":
            result.review_status = ReviewStatus.TRUNCATED
            result.budget.status = BudgetStatus.TRUNCATED
        elif completion == "failed":
            result.review_status = ReviewStatus.FAILED
            result.reviewer.failure_reason = ReviewerFailureReason.OUTPUT_MALFORMED
        preserve_run_artifacts = keep_review_artifacts or completion == "failed"
        audit = build_audit_graph(
            review_result=result,
            skeleton=skeleton,
            hunk_index=hunk_index,
            overall_assessment=_overall_assessment(raw_analysis),
        )
        assert_valid_audit(audit)
        diff_version = audit_diff_version(audit)
        if diff_version is None:
            raise AuditWorkflowError("finalized audit is missing diff_version")
        _atomic_write_json(staging_dir / "audit.json", audit)
        if preserve_run_artifacts:
            _atomic_write_json(run_dir / "review-result.json", to_serializable(result))
        render_audit_file(staging_dir / "audit.json", staging_dir / "audit.html")
    except (AuditWorkflowError, AuditValidationError, AuditRenderError, ValueError, KeyError) as exc:
        raise AuditWorkflowError(f"finalize validation failed: {exc}", staging_dir=staging_dir) from exc

    if _lexists(final_dir):
        raise AuditWorkflowError(
            f"final output leaf appeared before publication: {final_dir}",
            staging_dir=staging_dir,
        )
    if not preserve_run_artifacts:
        try:
            shutil.rmtree(run_dir)
        except OSError as exc:
            raise AuditWorkflowError(
                f"cannot clean review artifacts: {exc}", staging_dir=staging_dir
            ) from exc
    try:
        os.rename(staging_dir, final_dir)
    except OSError as exc:
        _record_finalize_failure(staging_dir, f"directory publication failed: {exc}")
        raise AuditWorkflowError(
            f"cannot publish audit artifact pair: {exc}", staging_dir=staging_dir
        ) from exc

    audit_json = final_dir / "audit.json"
    audit_html = final_dir / "audit.html"
    if not audit_json.is_file() or not audit_html.is_file():
        raise AuditWorkflowError("published directory does not contain the complete artifact pair")
    return {
        "run_id": run_id,
        "final_dir": str(final_dir),
        "audit_json": str(audit_json),
        "audit_html": str(audit_html),
        "review_status": audit["summary"]["review_status"],
        "verdict": audit["summary"]["verdict"],
        "diff_version": diff_version,
        "report_version": content_version(audit_json.read_bytes()),
    }
