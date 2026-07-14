"""Host-integrated ingest pipeline: raw analysis → ReviewResult.

This module owns the post-reviewer path for host-integrated mode.
The host executes the canonical prompt with its available LLM context and
passes the raw analysis text back. This module runs normalizer + adjudicator
to produce a standard ReviewResult without calling an LLM.
"""

from __future__ import annotations

from .adjudicator import determine_advisory_verdict, determine_intent_coverage
from .normalizer import declared_finding_ids, normalize_review_output
from .pack import compute_pack_completeness
from .schema import (
    BudgetStatus,
    ReviewPack,
    ReviewResult,
    ReviewStatus,
    ReviewerMeta,
    ResultBudget,
    SCHEMA_VERSION,
)


def run_ingest(
    pack: ReviewPack,
    raw_analysis: str,
    *,
    model: str,
    prompt_source: str | None = None,
    prompt_version: str | None = None,
    latency_sec: float | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> ReviewResult:
    """Run the ingest pipeline for host-integrated review.

    The host has already given the canonical prompt to its model for review.
    This function takes the raw analysis text and produces a ReviewResult
    by running normalizer + adjudicator. No LLM call is made.

    The host manages its own context window. Budget fields record the observed
    input size as follows:
      - status = COMPLETE
      - files_reviewed = files_total = len(pack.changed_files)
      - chars_consumed = len(pack.diff)
      - chars_limit = pack.budget.max_chars_total
    """
    pack_completeness = compute_pack_completeness(pack)
    files_total = len(pack.changed_files)

    normalization = normalize_review_output(
        raw_analysis,
        pack,
        pack_completeness=pack_completeness,
    )
    declared_ids = declared_finding_ids(raw_analysis)
    parsed_ids = tuple(finding.id for finding in normalization.raw_findings)
    output_contract_complete = (
        normalization.contract_complete and declared_ids == parsed_ids
    )
    advisory_verdict = determine_advisory_verdict(
        findings=normalization.findings,
        pack=pack,
        budget_status=BudgetStatus.COMPLETE,
        pack_completeness=pack_completeness,
        speculative_ratio=normalization.quality_metrics.speculative_ratio,
    )
    reviewer = ReviewerMeta(
        model=model,
        raw_analysis=raw_analysis,
        prompt_source=prompt_source,
        prompt_version=prompt_version,
        latency_sec=latency_sec,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    result_budget = ResultBudget(
        status=BudgetStatus.COMPLETE,
        files_reviewed=files_total,
        files_total=files_total,
        chars_consumed=len(pack.diff),
        chars_limit=pack.budget.max_chars_total,
    )

    findings = normalization.findings
    return ReviewResult(
        schema_version=SCHEMA_VERSION,
        artifact_fingerprint=pack.artifact_fingerprint,
        pack_fingerprint=pack.pack_fingerprint,
        review_status=(
            ReviewStatus.COMPLETE
            if output_contract_complete
            else ReviewStatus.TRUNCATED
        ),
        intent_coverage=determine_intent_coverage(pack, findings),
        raw_findings=normalization.raw_findings,
        findings=findings,
        evidence=list(pack.evidence or []),
        advisory_verdict=advisory_verdict,
        quality_metrics=normalization.quality_metrics,
        reviewer=reviewer,
        budget=result_budget,
    )
