"""Tests for deterministic finding normalization."""

from __future__ import annotations

from change_audit.review.normalizer import declared_finding_ids, normalize_review_output
from change_audit.review.schema import (
    Confidence,
    ContextFile,
    Evidence,
    EvidenceStatus,
    FileMeta,
    Locatability,
    ReviewPack,
    Severity,
)


PACK = ReviewPack(
    diff="diff --git a/src/auth.py b/src/auth.py\n@@ -1 +1 @@\n-print('a')\n+print('b')\n",
    changed_files=[FileMeta(path="src/auth.py", language="python")],
    artifact_fingerprint="artifact",
    pack_fingerprint="pack",
    evidence=[
        Evidence(
            source="pytest",
            status=EvidenceStatus.FAIL,
            summary="src/auth.py failed",
            detail="src/auth.py::test_auth failed",
        )
    ],
    context_files=[ContextFile(path="plan.md", content="context")],
)


RAW_OUTPUT = """\
## Section 1: Findings

**f-001**
- **Where**: `src/auth.py`, line 42
- **What**: Missing null guard causes a crash in the new code path.
- **Why**: The diff removes the only None check before the value is dereferenced.
- **Severity estimate**: HIGH
- **Category**: logic_error

**f-002**
- **Where**: `src/auth.py`
- **What**: This might break callers in edge cases.
- **Why**: Possibly depends on behavior outside the diff.
- **Severity estimate**: MEDIUM
- **Category**: suggestion

## Section 2: Observations

**o-001**
- **Where**: `src/auth.py`
- **What**: observation only
- **Why**: not diff-verifiable
"""


class TestNormalizer:
    def test_parses_findings_and_ignores_observations(self):
        result = normalize_review_output(RAW_OUTPUT, PACK)
        assert result.raw_findings_count == 2
        assert len(result.raw_findings) == 2
        assert len(result.findings) == 2
        assert result.findings[0].id == "f-001"
        assert result.findings[0].locatability == Locatability.EXACT

    def test_parses_embedded_line_range_before_later_mixed_location(self):
        raw = """\
## Section 1: Findings

### f-001
- **Where**: `src/auth.py:42-48` and `src/other.py`, line 71, @@ -71 +71 @@
- **What**: Missing validation on the first changed branch.
- **Why**: The first branch dereferences the value before checking it.
- **Severity estimate**: MEDIUM
- **Category**: logic_error
"""
        result = normalize_review_output(raw, PACK)
        finding = result.findings[0]
        assert finding.file == "src/auth.py"
        assert finding.line == 42
        assert finding.diff_hunk is None
        assert finding.locatability == Locatability.EXACT

    def test_parses_same_file_multi_range_location_from_real_host_output(self):
        for location, expected_line in (
            ("`src/auth.py:215-230, 346-350`", 215),
            ("`src/auth.py:253-343, 420`", 253),
        ):
            raw = f"""\
## Section 1: Findings

### f-001
- **Where**: {location}
- **What**: Multiple changed regions expose one concrete failure.
- **Why**: The first changed region is sufficient to anchor the issue.
- **Severity estimate**: MEDIUM
- **Category**: logic_error
"""
            finding = normalize_review_output(raw, PACK).findings[0]
            assert finding.file == "src/auth.py"
            assert finding.line == expected_line
            assert finding.locatability == Locatability.EXACT

    def test_multi_file_token_is_not_misparsed_as_one_exact_location(self):
        raw = """\
## Section 1: Findings

### f-001
- **Where**: `src/auth.py:42-48, src/other.py:71-72`
- **What**: The report combines two distinct file locations.
- **Why**: A single exact anchor cannot represent both files.
- **Severity estimate**: MEDIUM
- **Category**: logic_error
"""
        finding = normalize_review_output(raw, PACK).findings[0]
        assert finding.line is None
        assert finding.locatability == Locatability.FILE_ONLY

    def test_trusted_path_ending_in_colon_digits_remains_a_file_path(self):
        pack = ReviewPack(
            diff="diff --git a/src/spec:2026 b/src/spec:2026\n",
            changed_files=[FileMeta(path="src/spec:2026")],
            artifact_fingerprint="artifact",
            pack_fingerprint="pack",
        )
        raw = """\
## Section 1: Findings

### f-001
- **Where**: `src/spec:2026`
- **What**: The trusted path itself ends with numeric characters.
- **Why**: It must not be rewritten as a path and line pair.
- **Severity estimate**: LOW
- **Category**: documentation
"""
        finding = normalize_review_output(raw, pack).findings[0]
        assert finding.file == "src/spec:2026"
        assert finding.line is None
        assert finding.locatability == Locatability.FILE_ONLY

    def test_parses_bare_finding_ids(self):
        """Regression: bare f-001 (no bold/heading) must be parsed."""
        raw = """\
## Section 1: Findings

f-001
- **Where**: `src/auth.py`, line 42
- **What**: Missing null guard.
- **Why**: Removed None check.
- **Severity estimate**: HIGH
- **Category**: logic_error

f-002
- **Where**: `src/auth.py`
- **What**: Edge case risk.
- **Why**: Depends on external behavior.
- **Severity estimate**: LOW
- **Category**: spec_mismatch

## Section 2: Observations
"""
        result = normalize_review_output(raw, PACK)
        assert result.raw_findings_count == 2
        assert result.findings[0].id == "f-001"
        assert result.findings[1].id == "f-002"

    def test_malformed_finding_id_is_declared_but_fails_the_contract(self):
        raw = """\
## Section 1: Findings

### f-001
- **Where**: `src/auth.py`, line 1
- **What**: The valid block remains parseable.
- **Why**: The changed line proves the issue.
- **Severity estimate**: MEDIUM
- **Category**: logic_error

### f-2
- **Where**: `src/auth.py`, line 1
- **What**: This malformed identifier must not disappear silently.
- **Why**: The output contract requires three digits.
- **Severity estimate**: LOW
- **Category**: other
"""

        result = normalize_review_output(raw, PACK)

        assert declared_finding_ids(raw) == ("f-001", "f-2")
        assert [finding.id for finding in result.raw_findings] == ["f-001"]
        assert result.contract_complete is False

    def test_confidence_and_constraints_are_applied(self):
        result = normalize_review_output(RAW_OUTPUT, PACK)
        first, second = result.findings
        assert first.severity == Severity.HIGH
        assert first.confidence == Confidence.PLAUSIBLE
        assert first.evidence_related_file is True
        assert second.confidence == Confidence.SPECULATIVE
        assert second.severity == Severity.MEDIUM
        assert second.actionable is False

    def test_chinese_hedge_is_not_treated_as_actionable_certainty(self):
        raw = """\
## Section 1: Findings

### f-001
- **Where**: `src/auth.py`, line 42
- **What**: 这个改动可能导致调用方在边界条件下失败。
- **Why**: 如果外部仍传入空值，就会触发异常。
- **Severity estimate**: MEDIUM
- **Category**: logic_error
"""
        finding = normalize_review_output(raw, PACK).findings[0]
        assert finding.confidence == Confidence.SPECULATIVE
        assert finding.actionable is False

    def test_noise_cap_truncates(self):
        result = normalize_review_output(RAW_OUTPUT, PACK, max_findings=1)
        assert result.raw_findings_count == 2
        assert len(result.raw_findings) == 2
        assert result.emitted_findings_count == 1
        assert len(result.findings) == 1
        assert result.findings[0].id == "f-001"
        assert result.noise_count >= 1

    def test_noise_cap_sorts_by_constrained_severity_before_truncation(self):
        raw = """\
## Section 1: Findings

**f-001**
- **Where**: `src/auth.py`
- **What**: Minor style issue in the new code path.
- **Why**: Style only.
- **Severity estimate**: LOW
- **Category**: style

**f-002**
- **Where**: `src/auth.py`, line 8
- **What**: Missing authorization check allows unintended access.
- **Why**: The new branch returns before the auth guard runs.
- **Severity estimate**: HIGH
- **Category**: logic_error
"""
        result = normalize_review_output(raw, PACK, max_findings=1)
        assert [finding.id for finding in result.raw_findings] == ["f-001", "f-002"]
        assert [finding.id for finding in result.findings] == ["f-002"]

    def test_noise_cap_prefers_evidence_related_file_on_severity_tie(self):
        raw = """\
## Section 1: Findings

**f-001**
- **Where**: `src/other.py`, line 5
- **What**: Missing validation in the new branch causes a crash.
- **Why**: The diff removed the guard before dereferencing the value.
- **Severity estimate**: MEDIUM
- **Category**: logic_error

**f-002**
- **Where**: `src/auth.py`, line 7
- **What**: Missing validation in the auth branch causes a crash.
- **Why**: The diff removed the guard before dereferencing the value.
- **Severity estimate**: MEDIUM
- **Category**: logic_error
"""
        pack = ReviewPack(
            diff=PACK.diff,
            changed_files=[
                FileMeta(path="src/auth.py", language="python"),
                FileMeta(path="src/other.py", language="python"),
            ],
            artifact_fingerprint="artifact",
            pack_fingerprint="pack",
            evidence=[
                Evidence(
                    source="pytest",
                    status=EvidenceStatus.FAIL,
                    summary="src/auth.py failed",
                    detail="src/auth.py::test_auth failed",
                )
            ],
        )
        result = normalize_review_output(raw, pack, max_findings=1)
        assert [finding.id for finding in result.raw_findings] == ["f-001", "f-002"]
        assert [finding.id for finding in result.findings] == ["f-002"]

    def test_supports_heading_style_ids(self):
        raw = """\
## Section 1: Findings

### f-001
- **Where**: `src/auth.py`, line 3
- **What**: Missing validation on the new branch.
- **Why**: The guard was removed from the diff.
- **Severity estimate**: MEDIUM
- **Category**: missing_validation
"""
        result = normalize_review_output(raw, PACK)
        assert len(result.findings) == 1
        assert result.findings[0].category == "missing_validation"

    def test_evidence_related_file_does_not_match_substring(self):
        pack = ReviewPack(
            diff=PACK.diff,
            changed_files=[FileMeta(path="a.py", language="python")],
            artifact_fingerprint="artifact",
            pack_fingerprint="pack",
            evidence=[
                Evidence(
                    source="pytest",
                    status=EvidenceStatus.FAIL,
                    summary="data.py failed",
                    detail="data.py::test_case failed",
                )
            ],
        )
        raw = """\
## Section 1: Findings

**f-001**
- **Where**: `a.py`, line 2
- **What**: Missing validation in the new path.
- **Why**: The check was removed in the diff.
- **Severity estimate**: LOW
- **Category**: missing_validation
"""
        result = normalize_review_output(raw, pack)
        assert result.findings[0].evidence_related_file is False

    def test_pack_completeness_is_computed_inside_normalizer(self):
        result = normalize_review_output(RAW_OUTPUT, PACK)
        assert result.quality_metrics.pack_completeness > 0.0

    def test_observations_not_absorbed_into_last_finding_category(self):
        """Regression: ## Observations after findings must not pollute the
        last finding's category field (normalizer category pollution)."""
        raw = """\
## Section 1: Findings

**f-001**
- **Where**: `src/auth.py`, line 35
- **What**: URL classifier uses substring match instead of host parsing.
- **Why**: A proxy URL containing the target hostname would be misrouted.
- **Severity estimate**: MEDIUM
- **Category**: missing_validation

**f-002**
- **Where**: `src/auth.py`, line 39
- **What**: Trailing slash handling misses nested paths.
- **Why**: URLs like /openai/v1 are not excluded by the endswith check.
- **Severity estimate**: MEDIUM
- **Category**: logic_error

## Observations

- The routing logic depends on exact URL conventions.
- Additional tests around proxy hostnames would reduce risk.

## Overall Assessment

The changes address real concerns but the URL classifier is too loose.
"""
        result = normalize_review_output(raw, PACK)
        assert len(result.findings) == 2
        assert result.findings[0].category == "missing_validation"
        assert result.findings[1].category == "logic_error"
        # Ensure no observation text leaked into categories
        for f in result.findings:
            assert len(f.category) < 50, (
                f"category '{f.category[:60]}...' looks polluted"
            )

    def test_heading_with_colon_description(self):
        """Regression: ### f-001: description text must be parsed."""
        raw = """\
## Section 1: Findings

### f-001: Version mismatch between __init__.py and pyproject.toml
- **Where**: `crossreview/__init__.py`, line 3
- **What**: Hardcoded version does not match pyproject.toml.
- **Why**: Package will report wrong version at runtime.
- **Severity estimate**: HIGH
- **Category**: spec_mismatch

### f-002: Docs version not bumped
- **Where**: `docs/example.md`, line 10
- **What**: Documentation example still shows old version.
- **Why**: Release checklist was incomplete.
- **Severity estimate**: MEDIUM
- **Category**: spec_mismatch
"""
        result = normalize_review_output(raw, PACK)
        assert result.raw_findings_count == 2
        assert result.findings[0].id == "f-001"
        assert result.findings[0].summary.startswith("Hardcoded version")
        assert result.findings[1].id == "f-002"

    def test_field_without_dash_prefix(self):
        """Regression: **Where**: (no dash prefix) must be parsed."""
        raw = """\
## Section 1: Findings

### f-001: Missing null check
**Where**: `src/auth.py`, line 42
**What**: Null guard missing in the new code path.
**Why**: The diff removes the None check before dereferencing.
**Severity**: HIGH
**Category**: logic_error
"""
        result = normalize_review_output(raw, PACK)
        assert result.raw_findings_count == 1
        assert result.findings[0].severity == Severity.HIGH
        assert result.findings[0].file == "src/auth.py"
        assert result.findings[0].line == 42
        assert result.findings[0].summary.startswith("Null guard missing")

    def test_severity_label_alias(self):
        """Regression: **Severity**: must work alongside **Severity estimate**:."""
        raw_with_alias = """\
## Section 1: Findings

**f-001**
- **Where**: `src/auth.py`, line 5
- **What**: Missing input validation in the handler.
- **Why**: User-supplied value is used without sanitization.
- **Severity**: MEDIUM
- **Category**: missing_validation
"""
        raw_canonical = raw_with_alias.replace("- **Severity**:", "- **Severity estimate**:")
        result_alias = normalize_review_output(raw_with_alias, PACK)
        result_canonical = normalize_review_output(raw_canonical, PACK)
        assert result_alias.findings[0].severity == result_canonical.findings[0].severity
        assert result_alias.findings[0].severity == Severity.MEDIUM

    def test_severity_with_markdown_bold_and_description(self):
        """Regression: **Severity**: **High** — blocks release must parse as HIGH."""
        raw = """\
## Section 1: Findings

### f-001 | Version mismatch
- **Where**: `pkg/__init__.py`, line 3
- **What**: Version does not match pyproject.toml.
- **Why it matters**: Package reports wrong version at runtime.
- **Severity**: **High** — blocks a correct release.
- **Category**: spec_mismatch
"""
        result = normalize_review_output(raw, PACK)
        assert result.findings[0].severity == Severity.HIGH

    def test_severity_space_padded_bold(self):
        """Regression: ** high ** must parse as HIGH, not silently fall to LOW."""
        raw = """\
## Section 1: Findings

**f-001**
- **Where**: `src/auth.py`, line 5
- **What**: Missing input validation in the handler.
- **Why**: User-supplied value is used without sanitization.
- **Severity**: ** high **
- **Category**: missing_validation
"""
        result = normalize_review_output(raw, PACK)
        assert result.findings[0].severity == Severity.HIGH

    def test_host_first_spike_format_no_false_pass(self):
        """End-to-end regression: real host-first spike output must not produce
        a silent false-pass. Reviewer reports 3 findings; normalizer must extract
        all 3 and verdict must not be pass_candidate."""
        from change_audit.review.adjudicator import determine_advisory_verdict
        from change_audit.review.schema import BudgetStatus

        raw = """\
## Section 1: Findings

### f-001: Version mismatch between __init__.py and pyproject.toml
**Where**: `src/auth.py` line 3
**What**: Version string does not match pyproject.toml version.
**Why**: Package will report wrong version at runtime.
**Severity**: HIGH
**Category**: spec_mismatch

### f-002: Docs version stale
**Where**: `docs/example.md` line 10
**What**: Documentation example shows old version.
**Why**: Release checklist was incomplete.
**Severity**: MEDIUM
**Category**: spec_mismatch

### f-003: Changelog vs implementation mismatch
**Where**: `CHANGELOG.md` line 4
**What**: Changelog documents release but code not bumped.
**Why**: Incomplete version bump process.
**Severity**: HIGH
**Category**: logic_error

## Section 2: Observations

No additional observations.

## Section 3: Overall Assessment

Two HIGH and one MEDIUM finding. Release is not ready.
"""
        normalization = normalize_review_output(raw, PACK, pack_completeness=0.75)
        assert normalization.raw_findings_count == 3
        assert normalization.emitted_findings_count == 3

        verdict = determine_advisory_verdict(
            findings=normalization.findings,
            pack=PACK,
            budget_status=BudgetStatus.COMPLETE,
            pack_completeness=0.75,
            speculative_ratio=normalization.quality_metrics.speculative_ratio,
        )
        assert verdict.verdict.value != "pass_candidate", (
            f"False pass: reviewer found 3 issues but verdict is {verdict.verdict.value}"
        )
