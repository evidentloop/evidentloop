"""Pure summary calculation for audit findings."""

from __future__ import annotations

from typing import Any, Collection, Iterable, Mapping


_SEVERITY_ORDER = {"high": 4, "medium": 3, "low": 2, "note": 1}


def needs_human_triage(
    finding: Mapping[str, Any],
    *,
    has_trusted_file_association: bool | None = None,
) -> bool:
    """Open finding requires triage when downgraded from bug or lacking trusted file association."""
    if not finding.get("file_path") or has_trusted_file_association is False:
        return True
    extension = finding.get("extensions", {}).get("evidentloop", {})
    if not isinstance(extension, Mapping):
        return False
    return extension.get("downgraded_from") == "bug"


def compute_overall_severity(open_findings: Iterable[Mapping[str, Any]]) -> str | None:
    items = list(open_findings)
    if not items:
        return None
    return max(
        (str(f["severity"]) for f in items),
        key=lambda s: _SEVERITY_ORDER.get(s, 0),
    )


def build_summary(
    findings: Iterable[Mapping[str, Any]],
    fixes: Iterable[Mapping[str, Any]],
    *,
    review_status: str,
    empty_verdict: str = "inconclusive",
    force_inconclusive: bool = False,
    trusted_finding_ids: Collection[str] | None = None,
) -> dict[str, Any]:
    """Calculate verdict, overall severity, and counts without mutating graph entities."""
    finding_items = list(findings)
    fix_items = list(fixes)
    open_findings = [item for item in finding_items if item["status"] == "open"]

    if review_status != "complete":
        verdict = "inconclusive"
        overall_severity = None
    elif force_inconclusive:
        verdict = "inconclusive"
        overall_severity = compute_overall_severity(open_findings)
    elif open_findings:
        triage = [
            finding
            for finding in open_findings
            if needs_human_triage(
                finding,
                has_trusted_file_association=(
                    str(finding["id"]) in trusted_finding_ids
                    if trusted_finding_ids is not None
                    else None
                ),
            )
        ]
        if len(triage) == len(open_findings):
            verdict = "needs_human_triage"
        else:
            verdict = "concerns"
        overall_severity = compute_overall_severity(open_findings)
    elif empty_verdict == "pass_candidate":
        verdict = "pass_candidate"
        overall_severity = None
    else:
        verdict = "inconclusive"
        overall_severity = None

    return {
        "review_status": review_status,
        "verdict": verdict,
        "overall_severity": overall_severity,
        "finding_count": len(finding_items),
        "open_finding_count": len(open_findings),
        "fix_count": len(fix_items),
        "fix_done_count": sum(item["status"] == "done" for item in fix_items),
    }
