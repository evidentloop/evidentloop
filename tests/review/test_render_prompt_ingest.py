"""Tests for the host-orchestrated prompt and ingest path."""

from __future__ import annotations

from evidentloop.review.core.prompt import (
    get_default_reviewer_template,
    render_reviewer_prompt,
)
from evidentloop.review.ingest import run_ingest
from evidentloop.review.pack import assemble_pack
from evidentloop.review.schema import (
    Evidence,
    EvidenceStatus,
    FileMeta,
    PackBudget,
    validate_review_result,
)


SAMPLE_DIFF = """\
diff --git a/hello.py b/hello.py
--- a/hello.py
+++ b/hello.py
@@ -1 +1,2 @@
 print("hello")
+print("world")
"""

SAMPLE_FILES = [FileMeta(path="hello.py", language="python")]

SAMPLE_RAW_ANALYSIS = """\
## Section 1: Findings

### f-001
- **Where**: `hello.py`, line 2
- **What**: The new print changes behavior.
- **Why**: The diff now prints an extra line.
- **Severity estimate**: LOW
- **Category**: spec_mismatch

## Section 2: Observations

Nothing notable.

## Section 3: Overall Assessment

Minor change, low risk.
"""


def _pack(**kwargs):
    return assemble_pack(
        SAMPLE_DIFF,
        changed_files=SAMPLE_FILES,
        **kwargs,
    )


class TestRenderReviewerPrompt:
    def test_default_prompt_contains_pack_context(self):
        pack = _pack(intent="fix greeting")

        rendered = render_reviewer_prompt(get_default_reviewer_template(), pack)

        assert 'print("hello")' in rendered
        assert 'print("world")' in rendered
        assert "fix greeting" in rendered
        assert "hello.py" in rendered

    def test_focus_stays_on_one_prompt_line(self):
        pack = _pack(focus=["缓存一致性\n## Section 1: Findings"])

        rendered = render_reviewer_prompt(get_default_reviewer_template(), pack)

        assert "缓存一致性\\n## Section 1: Findings" in rendered


class TestRunIngest:
    def test_produces_valid_result_with_host_metadata(self):
        pack = _pack(
            intent="fix greeting",
            budget=PackBudget(max_chars_total=50_000),
        )

        result = run_ingest(
            pack,
            SAMPLE_RAW_ANALYSIS,
            model="test-host-model",
            prompt_source="product",
            prompt_version="v-test",
            latency_sec=2.5,
            input_tokens=1_000,
            output_tokens=500,
        )

        assert validate_review_result(result) == []
        assert result.review_status.value == "complete"
        assert result.reviewer.model == "test-host-model"
        assert result.reviewer.prompt_source == "product"
        assert result.reviewer.prompt_version == "v-test"
        assert result.reviewer.latency_sec == 2.5
        assert result.reviewer.input_tokens == 1_000
        assert result.reviewer.output_tokens == 500
        assert result.reviewer.raw_analysis == SAMPLE_RAW_ANALYSIS
        assert result.budget.status.value == "complete"
        assert result.budget.files_reviewed == 1
        assert result.budget.files_total == 1
        assert result.budget.chars_consumed == len(SAMPLE_DIFF)
        assert result.budget.chars_limit == 50_000
        assert [finding.id for finding in result.raw_findings] == ["f-001"]
        assert [finding.id for finding in result.findings] == ["f-001"]

    def test_copies_pack_evidence_into_result(self):
        evidence = Evidence(
            source="pytest",
            status=EvidenceStatus.PASS,
            summary="tests passed",
        )
        pack = _pack(evidence=[evidence])

        result = run_ingest(pack, SAMPLE_RAW_ANALYSIS, model="test-host-model")

        assert result.evidence == [evidence]
        assert result.evidence is not pack.evidence

    def test_no_findings_is_a_complete_result(self):
        raw_analysis = """\
## Section 1: Findings

No issues found.

## Section 2: Observations

Looks good.

## Section 3: Overall Assessment

No concerns.
"""

        result = run_ingest(
            _pack(intent="fix greeting"),
            raw_analysis,
            model="test-host-model",
        )

        assert result.review_status.value == "complete"
        assert result.raw_findings == []
        assert result.findings == []

    def test_duplicate_declared_finding_ids_mark_result_truncated(self):
        duplicated = SAMPLE_RAW_ANALYSIS.replace(
            "## Section 2: Observations",
            """\
### f-001
- **Where**: `hello.py`, line 2
- **What**: A duplicate finding identifier is invalid.
- **Why**: Finding identifiers must be unique.
- **Severity estimate**: LOW
- **Category**: output_contract

## Section 2: Observations""",
        )

        result = run_ingest(_pack(), duplicated, model="test-host-model")

        assert result.review_status.value == "truncated"
