"""ReviewResult to Audit Graph mapping, anchoring and scoring tests."""

from __future__ import annotations

from typing import Any

import pytest

from evidentloop.audit.adapter import SEVERITY_WEIGHTS, build_audit_graph
from evidentloop.review.ingest import run_ingest
from evidentloop.review.pack import assemble_pack
from evidentloop.review.schema import FileMeta, ReviewStatus
from evidentloop.validation import assert_valid_audit


DIFF = """\
diff --git a/app.py b/app.py
index 3d18d6f..2c0b7d0 100644
--- a/app.py
+++ b/app.py
@@ -1 +1 @@
-value = 1
+value = 2
"""
HUNK = "@@ -1 +1 @@\n-value = 1\n+value = 2"


def _parts() -> tuple[Any, dict[str, Any], dict[str, Any]]:
    pack = assemble_pack(DIFF, changed_files=[FileMeta(path="app.py", language="python")])
    skeleton = {
        "run_id": "run-adapter",
        "graph_id": "audit:run-adapter",
        "source": {"type": "git_diff", "ref": "HEAD~1"},
        "run": {
            "id": "run-adapter",
            "label": "Adapter test",
            "status": "inconclusive",
            "summary": "pending",
        },
        "change": {
            "id": "change-001",
            "type": "change",
            "title": "Change app value",
            "summary": "Updates the value.",
        },
        "files": [
            {
                "id": "file-001",
                "type": "file",
                "path": "app.py",
                "change_type": "modified",
                "additions": 1,
                "deletions": 1,
            }
        ],
    }
    hunk_index = {
        "run_id": "run-adapter",
        "hunks": [
            {
                "hunk_id": "hunk:app:1:1",
                "file_path": "app.py",
                "old_start": 1,
                "old_count": 1,
                "new_start": 1,
                "new_count": 1,
                "header": "@@ -1 +1 @@",
                "snippet": HUNK,
            }
        ],
    }
    return pack, skeleton, hunk_index


def _raw(category: str, *, where: str = "`app.py`, line 1, @@ -1 +1 @@") -> str:
    return f"""\
## Section 1: Findings

**f-001**
- **Where**: {where}
- **What**: Updated value breaks the documented runtime behavior.
- **Why**: Consumers still require the previous value and now receive an incompatible result.
- **Severity estimate**: HIGH
- **Category**: {category}

## Section 2: Observations

None.

## Section 3: Overall Assessment

The change has a concrete compatibility problem.
    """


def test_wave2_dogfood_freezes_severity_weights() -> None:
    assert SEVERITY_WEIGHTS == {"high": 40, "medium": 20, "low": 8, "note": 2}


@pytest.mark.parametrize(
    "source_category, expected",
    [
        ("logic_error", "bug"),
        ("correctness", "bug"),
        ("security", "risk"),
        ("performance", "risk"),
        ("missing_test", "quality"),
        ("maintainability", "quality"),
        ("spec_mismatch", "scope"),
        ("unexpected_family", "quality"),
    ],
)
def test_category_family_mapping(source_category: str, expected: str) -> None:
    pack, skeleton, hunk_index = _parts()
    result = run_ingest(pack, _raw(source_category), model="test-host")
    audit = build_audit_graph(
        review_result=result,
        skeleton=skeleton,
        hunk_index=hunk_index,
    )
    finding = next(item for item in audit["nodes"] if item["type"] == "finding")
    assert finding["category"] == expected
    assert finding["extensions"]["evidentloop"]["original_category"] == source_category
    assert_valid_audit(audit)


def test_exact_bug_uses_only_trusted_hunk_and_stable_fingerprint() -> None:
    pack, skeleton, hunk_index = _parts()
    result = run_ingest(pack, _raw("logic_error"), model="test-host")
    audit = build_audit_graph(
        review_result=result,
        skeleton=skeleton,
        hunk_index=hunk_index,
    )
    finding = next(item for item in audit["nodes"] if item["type"] == "finding")
    assert finding["category"] == "bug"
    assert finding["hunk_id"] == "hunk:app:1:1"
    assert finding["hunk"] == HUNK
    assert finding["highlight_lines"] == [1]
    assert finding["line_side"] == "new"
    evidence = next(item for item in audit["nodes"] if item["type"] == "evidence")
    assert evidence["source"] == "host_llm"
    assert evidence["summary"].startswith("宿主语义审查结论：")
    assert not any(node["type"] == "fix" for node in audit["nodes"])


def test_context_line_is_not_promoted_to_a_changed_line_anchor() -> None:
    pack, skeleton, hunk_index = _parts()
    hunk_index["hunks"][0].update(
        {
            "old_count": 2,
            "new_count": 2,
            "snippet": "@@ -1,2 +1,2 @@\n context\n-old value\n+new value",
        }
    )
    result = run_ingest(
        pack,
        _raw("logic_error", where="`app.py`, line 1"),
        model="test-host",
    )

    audit = build_audit_graph(
        review_result=result,
        skeleton=skeleton,
        hunk_index=hunk_index,
    )

    finding = next(item for item in audit["nodes"] if item["type"] == "finding")
    assert finding["category"] == "risk"
    assert "hunk" not in finding
    assert finding["extensions"]["evidentloop"]["downgrade_reason"] == (
        "line_outside_trusted_hunk"
    )
    assert audit["summary"]["unscored_finding_count"] == 1


def test_deleted_line_is_a_trusted_old_side_anchor() -> None:
    pack, skeleton, hunk_index = _parts()
    hunk_index["hunks"][0].update(
        {
            "old_count": 2,
            "new_count": 1,
            "snippet": "@@ -1,2 +1 @@\n context\n-removed value",
        }
    )
    result = run_ingest(
        pack,
        _raw("logic_error", where="`app.py`, line 2"),
        model="test-host",
    )

    audit = build_audit_graph(
        review_result=result,
        skeleton=skeleton,
        hunk_index=hunk_index,
    )

    finding = next(item for item in audit["nodes"] if item["type"] == "finding")
    assert finding["category"] == "bug"
    assert finding["line_side"] == "old"
    assert finding["highlight_lines"] == [2]
    assert_valid_audit(audit)


def test_embedded_line_range_resolves_to_trusted_hunk() -> None:
    pack, skeleton, hunk_index = _parts()
    result = run_ingest(
        pack,
        _raw("logic_error", where="`app.py:1-1` and `app.py:1`"),
        model="test-host",
    )
    audit = build_audit_graph(
        review_result=result,
        skeleton=skeleton,
        hunk_index=hunk_index,
    )

    finding = next(item for item in audit["nodes"] if item["type"] == "finding")
    assert finding["file_path"] == "app.py"
    assert finding["hunk_id"] == "hunk:app:1:1"
    assert finding["start_line"] == 1
    assert "downgraded_from" not in finding["extensions"]["evidentloop"]
    assert finding["fingerprint"].startswith("sha256:")
    assert audit["summary"]["risk_score"] == 40
    assert audit["summary"]["verdict"] == "concerns"


def test_same_file_multi_range_uses_first_segment_for_trusted_anchor() -> None:
    pack, skeleton, hunk_index = _parts()
    result = run_ingest(
        pack,
        _raw("logic_error", where="`app.py:1-1, 999-1000`"),
        model="test-host",
    )
    audit = build_audit_graph(
        review_result=result,
        skeleton=skeleton,
        hunk_index=hunk_index,
    )

    finding = next(item for item in audit["nodes"] if item["type"] == "finding")
    assert finding["category"] == "bug"
    assert finding["file_path"] == "app.py"
    assert finding["start_line"] == 1
    assert finding["hunk_id"] == "hunk:app:1:1"
    assert "downgraded_from" not in finding["extensions"]["evidentloop"]


@pytest.mark.parametrize(
    "where",
    [
        "`app.py`, line 1",
        "`app.py`, @@ -1 +1 @@",
    ],
)
def test_line_or_unique_header_can_resolve_exact_anchor(where: str) -> None:
    pack, skeleton, hunk_index = _parts()
    result = run_ingest(pack, _raw("correctness", where=where), model="test-host")
    audit = build_audit_graph(
        review_result=result,
        skeleton=skeleton,
        hunk_index=hunk_index,
    )
    finding = next(item for item in audit["nodes"] if item["type"] == "finding")
    assert finding["category"] == "bug"
    assert finding["hunk_id"] == "hunk:app:1:1"
    assert finding["line_side"] == "new"
    assert_valid_audit(audit)


def test_forged_header_or_line_downgrades_bug_without_copying_text() -> None:
    pack, skeleton, hunk_index = _parts()
    result = run_ingest(
        pack,
        _raw("logic_error", where="`app.py`, line 999, @@ -900 +900 @@"),
        model="test-host",
    )
    audit = build_audit_graph(
        review_result=result,
        skeleton=skeleton,
        hunk_index=hunk_index,
    )
    finding = next(item for item in audit["nodes"] if item["type"] == "finding")
    extension = finding["extensions"]["evidentloop"]
    assert finding["category"] == "risk"
    assert finding["severity"] == "medium"
    assert "hunk" not in finding
    assert extension["downgraded_from"] == "bug"
    assert extension["downgrade_reason"] == "header_not_in_trusted_hunk"
    assert audit["summary"]["unscored_finding_count"] == 1
    assert audit["summary"]["risk_score"] is None
    assert audit["summary"]["verdict"] == "needs_human_triage"
    assert_valid_audit(audit)


def test_unsafe_path_is_never_promoted_to_a_file_or_hunk_anchor() -> None:
    pack, skeleton, hunk_index = _parts()
    result = run_ingest(
        pack,
        _raw("logic_error", where="`../app.py`, line 1, @@ -1 +1 @@"),
        model="test-host",
    )
    audit = build_audit_graph(
        review_result=result,
        skeleton=skeleton,
        hunk_index=hunk_index,
    )
    finding = next(item for item in audit["nodes"] if item["type"] == "finding")
    assert finding["category"] == "risk"
    assert "file_path" not in finding
    assert "hunk" not in finding
    assert finding["extensions"]["evidentloop"]["downgrade_reason"] == "unsafe_file_path"
    assert not any(edge["type"] == "finding_in_file" for edge in audit["edges"])
    assert_valid_audit(audit)


def test_non_bug_file_only_anchor_is_scored_without_fabricated_hunk() -> None:
    pack, skeleton, hunk_index = _parts()
    result = run_ingest(pack, _raw("security", where="`app.py`"), model="test-host")
    audit = build_audit_graph(
        review_result=result,
        skeleton=skeleton,
        hunk_index=hunk_index,
    )
    finding = next(item for item in audit["nodes"] if item["type"] == "finding")
    assert finding["category"] == "risk"
    assert finding["file_path"] == "app.py"
    assert "hunk" not in finding
    assert audit["summary"]["unscored_finding_count"] == 0
    assert audit["summary"]["risk_score"] == 20
    assert_valid_audit(audit)


def test_partial_and_clean_results_preserve_process_state() -> None:
    pack, skeleton, hunk_index = _parts()
    partial_result = run_ingest(pack, _raw("security"), model="test-host")
    partial_result.review_status = ReviewStatus.TRUNCATED
    partial = build_audit_graph(
        review_result=partial_result,
        skeleton=skeleton,
        hunk_index=hunk_index,
    )
    assert partial["summary"]["review_status"] == "partial"
    assert partial["summary"]["verdict"] == "inconclusive"
    assert partial["summary"]["risk_score"] is None

    clean_result = run_ingest(
        pack,
        "## Section 1: Findings\n\nNo findings.\n\n"
        "## Section 3: Overall Assessment\n\nClean.",
        model="test-host",
    )
    clean = build_audit_graph(
        review_result=clean_result,
        skeleton=skeleton,
        hunk_index=hunk_index,
    )
    assert clean["summary"]["review_status"] == "complete"
    assert clean["summary"]["verdict"] == "inconclusive"
    assert clean["summary"]["risk_score"] is None
    assert clean["summary"]["finding_count"] == 0
    assert_valid_audit(partial)
    assert_valid_audit(clean)


def test_finding_reason_is_not_fabricated_as_a_fix() -> None:
    pack, skeleton, hunk_index = _parts()
    result = run_ingest(pack, _raw("logic_error"), model="test-host")

    audit = build_audit_graph(
        review_result=result,
        skeleton=skeleton,
        hunk_index=hunk_index,
    )

    assert not any(node["type"] == "fix" for node in audit["nodes"])
    assert not any(edge["type"] == "requires_fix" for edge in audit["edges"])
    assert audit["summary"]["fix_count"] == 0
    assert_valid_audit(audit)
