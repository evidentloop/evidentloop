"""Tests for deterministic adjudicator rules."""

from __future__ import annotations

from change_audit.review.adjudicator import determine_advisory_verdict, determine_intent_coverage
from change_audit.review.schema import (
    BudgetStatus,
    Confidence,
    Evidence,
    EvidenceStatus,
    FileMeta,
    Finding,
    IntentCoverage,
    Locatability,
    ReviewPack,
    Severity,
    Verdict,
)


def _pack(*, intent: str | None = None, evidence: list[Evidence] | None = None) -> ReviewPack:
    return ReviewPack(
        diff="diff --git a/a.py b/a.py\n@@ -1 +1 @@\n-print('a')\n+print('b')\n",
        changed_files=[FileMeta(path="a.py", language="python")],
        artifact_fingerprint="artifact",
        pack_fingerprint="pack",
        intent=intent,
        evidence=evidence,
    )


def _finding(*, severity: Severity = Severity.LOW, category: str = "logic_error") -> Finding:
    return Finding(
        id="f-001",
        severity=severity,
        summary="summary that is long enough",
        detail="detail",
        category=category,
        locatability=Locatability.EXACT,
        confidence=Confidence.PLAUSIBLE,
        file="a.py",
        line=1,
    )


class TestIntentCoverage:
    def test_unknown_without_intent(self):
        assert determine_intent_coverage(_pack(), []) == IntentCoverage.UNKNOWN

    def test_partial_when_spec_mismatch_exists(self):
        assert determine_intent_coverage(
            _pack(intent="fix behavior"),
            [_finding(category="spec_mismatch")],
        ) == IntentCoverage.PARTIAL

    def test_covered_when_intent_present_and_no_spec_mismatch(self):
        assert determine_intent_coverage(
            _pack(intent="fix behavior"),
            [_finding(category="logic_error")],
        ) == IntentCoverage.COVERED


class TestAdjudicator:
    def test_rejected_is_inconclusive(self):
        verdict = determine_advisory_verdict(
            findings=[],
            pack=_pack(),
            budget_status=BudgetStatus.REJECTED,
            pack_completeness=1.0,
            speculative_ratio=0.0,
        )
        assert verdict.verdict == Verdict.INCONCLUSIVE

    def test_truncated_caps_to_concerns(self):
        verdict = determine_advisory_verdict(
            findings=[],
            pack=_pack(),
            budget_status=BudgetStatus.TRUNCATED,
            pack_completeness=1.0,
            speculative_ratio=0.0,
        )
        assert verdict.verdict == Verdict.CONCERNS

    def test_errorish_evidence_is_concerns(self):
        verdict = determine_advisory_verdict(
            findings=[],
            pack=_pack(evidence=[Evidence(source="pytest", status=EvidenceStatus.ERROR, summary="err")]),
            budget_status=BudgetStatus.COMPLETE,
            pack_completeness=1.0,
            speculative_ratio=0.0,
        )
        assert verdict.verdict == Verdict.CONCERNS

    def test_fail_without_findings_is_triage(self):
        verdict = determine_advisory_verdict(
            findings=[],
            pack=_pack(evidence=[Evidence(source="pytest", status=EvidenceStatus.FAIL, summary="fail")]),
            budget_status=BudgetStatus.COMPLETE,
            pack_completeness=1.0,
            speculative_ratio=0.0,
        )
        assert verdict.verdict == Verdict.NEEDS_HUMAN_TRIAGE

    def test_speculative_ratio_rule_is_reachable(self):
        verdict = determine_advisory_verdict(
            findings=[_finding(severity=Severity.LOW)],
            pack=_pack(),
            budget_status=BudgetStatus.COMPLETE,
            pack_completeness=1.0,
            speculative_ratio=0.75,
        )
        assert verdict.verdict == Verdict.CONCERNS
        assert "speculative" in verdict.rationale

    def test_fail_with_findings_is_concerns(self):
        verdict = determine_advisory_verdict(
            findings=[_finding(severity=Severity.LOW)],
            pack=_pack(evidence=[Evidence(source="pytest", status=EvidenceStatus.FAIL, summary="fail")]),
            budget_status=BudgetStatus.COMPLETE,
            pack_completeness=1.0,
            speculative_ratio=0.0,
        )
        assert verdict.verdict == Verdict.CONCERNS
        assert "evidence failed" in verdict.rationale

    def test_medium_or_high_finding_is_concerns(self):
        verdict = determine_advisory_verdict(
            findings=[_finding(severity=Severity.MEDIUM)],
            pack=_pack(),
            budget_status=BudgetStatus.COMPLETE,
            pack_completeness=1.0,
            speculative_ratio=0.0,
        )
        assert verdict.verdict == Verdict.CONCERNS

    def test_pass_candidate_requires_completeness(self):
        verdict = determine_advisory_verdict(
            findings=[],
            pack=_pack(),
            budget_status=BudgetStatus.COMPLETE,
            pack_completeness=0.8,
            speculative_ratio=0.0,
        )
        assert verdict.verdict == Verdict.PASS_CANDIDATE

    def test_low_completeness_without_findings_is_inconclusive(self):
        verdict = determine_advisory_verdict(
            findings=[],
            pack=_pack(),
            budget_status=BudgetStatus.COMPLETE,
            pack_completeness=0.3,
            speculative_ratio=0.0,
        )
        assert verdict.verdict == Verdict.INCONCLUSIVE
