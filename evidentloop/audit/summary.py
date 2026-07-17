"""Pure summary calculation for audit findings."""

from __future__ import annotations

from typing import Any, Iterable, Mapping


SEVERITY_WEIGHTS: dict[str, int] = {
    "high": 40,
    "medium": 20,
    "low": 8,
    "note": 2,
}


def is_unscored_finding(finding: Mapping[str, Any]) -> bool:
    """Return whether an open finding is intentionally excluded from risk scoring."""
    extension = finding.get("extensions", {}).get("evidentloop", {})
    return isinstance(extension, Mapping) and (
        extension.get("downgraded_from") == "bug" or extension.get("unscored") is True
    )


def build_summary(
    findings: Iterable[Mapping[str, Any]],
    fixes: Iterable[Mapping[str, Any]],
    *,
    review_status: str,
    empty_verdict: str = "inconclusive",
    force_inconclusive: bool = False,
) -> dict[str, Any]:
    """Calculate verdict, risk, and counts without mutating graph entities."""
    finding_items = list(findings)
    fix_items = list(fixes)
    open_findings = [item for item in finding_items if item["status"] == "open"]
    unscored = [item for item in open_findings if is_unscored_finding(item)]
    scored = [item for item in open_findings if item not in unscored]

    if review_status != "complete" or force_inconclusive:
        verdict = "inconclusive"
        risk_score: int | None = None
    elif scored:
        verdict = "concerns"
        risk_score = min(
            sum(SEVERITY_WEIGHTS[str(item["severity"])] for item in scored),
            100,
        )
    elif unscored:
        verdict = "needs_human_triage"
        risk_score = None
    elif empty_verdict == "pass_candidate":
        verdict = "pass_candidate"
        risk_score = 0
    else:
        verdict = "inconclusive"
        risk_score = None

    return {
        "review_status": review_status,
        "verdict": verdict,
        "risk_score": risk_score,
        "finding_count": len(finding_items),
        "unscored_finding_count": len(unscored),
        "open_finding_count": len(open_findings),
        "fix_count": len(fix_items),
        "fix_done_count": sum(item["status"] == "done" for item in fix_items),
    }
