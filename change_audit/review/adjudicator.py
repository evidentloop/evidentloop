"""Deterministic advisory verdict rules."""

from __future__ import annotations

from .schema import (
    AdvisoryVerdict,
    BudgetStatus,
    IntentCoverage,
    ReviewPack,
    Severity,
    Verdict,
    Finding,
)


def determine_intent_coverage(pack: ReviewPack, findings: list[Finding]) -> IntentCoverage:
    """Classify intent coverage for the current review result."""
    if not pack.intent:
        return IntentCoverage.UNKNOWN
    if any(finding.category == "spec_mismatch" for finding in findings):
        return IntentCoverage.PARTIAL
    return IntentCoverage.COVERED


def determine_advisory_verdict(
    *,
    findings: list[Finding],
    pack: ReviewPack,
    budget_status: BudgetStatus,
    pack_completeness: float,
    speculative_ratio: float,
) -> AdvisoryVerdict:
    """Produce a deterministic advisory verdict.

    Rule evaluation order (first match wins):
    1. rejected budget → INCONCLUSIVE
    2. truncated budget → CONCERNS
    3. evidence error/skipped → CONCERNS
    4. speculative_ratio > 50% → CONCERNS
    5. evidence failed + findings → CONCERNS
    6. medium/high findings → CONCERNS
    7. any findings → CONCERNS
    8. evidence failed + no findings → NEEDS_HUMAN_TRIAGE
    9. pack_completeness >= 0.7 → PASS_CANDIDATE
    10. fallback → INCONCLUSIVE
    """
    evidence = pack.evidence or []
    has_fail = any(item.status.value == "fail" for item in evidence)
    has_errorish = any(item.status.value in {"error", "skipped"} for item in evidence)
    has_medium_or_high = any(
        finding.severity in {Severity.HIGH, Severity.MEDIUM}
        for finding in findings
    )

    # 1. Budget rejected — cannot produce a meaningful verdict.
    if budget_status == BudgetStatus.REJECTED:
        return AdvisoryVerdict(
            verdict=Verdict.INCONCLUSIVE,
            rationale="review input was rejected by the budget gate",
        )

    # 2. Budget truncated — partial review, flag concerns regardless.
    if budget_status == BudgetStatus.TRUNCATED:
        return AdvisoryVerdict(
            verdict=Verdict.CONCERNS,
            rationale="review was truncated by budget limits",
        )

    # 3. Evidence collection issues — incomplete signal.
    if has_errorish:
        return AdvisoryVerdict(
            verdict=Verdict.CONCERNS,
            rationale="evidence collection was incomplete or errored",
        )

    # 4. Too speculative — even with findings present, a high speculative ratio
    #    means the reviewer struggled and should not look pass-like.
    if speculative_ratio > 0.5:
        return AdvisoryVerdict(
            verdict=Verdict.CONCERNS,
            rationale="review output was too speculative to justify pass_candidate",
        )

    # 5. Evidence failed and reviewer also found issues — still concerns, but
    #    call out the compounded signal explicitly.
    if has_fail and findings:
        return AdvisoryVerdict(
            verdict=Verdict.CONCERNS,
            rationale="deterministic evidence failed and reviewer also produced findings",
        )

    # 6-7. Findings present — severity determines rationale.
    if findings and has_medium_or_high:
        return AdvisoryVerdict(
            verdict=Verdict.CONCERNS,
            rationale="review found medium/high-severity issues",
        )

    if findings:
        return AdvisoryVerdict(
            verdict=Verdict.CONCERNS,
            rationale="review found issues that should be inspected",
        )

    # 8. Evidence failed but reviewer found nothing — suspicious.
    if has_fail:
        return AdvisoryVerdict(
            verdict=Verdict.NEEDS_HUMAN_TRIAGE,
            rationale="deterministic evidence failed but reviewer produced no findings",
        )

    # 9. Clean review with sufficient pack coverage.
    if pack_completeness >= 0.7:
        return AdvisoryVerdict(
            verdict=Verdict.PASS_CANDIDATE,
            rationale="no findings and pack completeness is sufficient for advisory pass",
        )

    # 10. Fallback — insufficient information for a pass.
    return AdvisoryVerdict(
        verdict=Verdict.INCONCLUSIVE,
        rationale="pack completeness was too low for an advisory pass",
    )
