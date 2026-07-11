"""Tests for budget gate behavior."""

from __future__ import annotations

from change_audit.review.budget import apply_budget_gate
from change_audit.review.schema import BudgetStatus, FileMeta, PackBudget, ReviewPack


DIFF = """\
diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1 +1,2 @@
-print("a")
+print("a")
+print("x")
diff --git a/service/auth.py b/service/auth.py
--- a/service/auth.py
+++ b/service/auth.py
@@ -1 +1,2 @@
-print("b")
+print("b")
+print("y")
"""


def _pack(*, max_files=None, max_chars_total=None, focus=None) -> ReviewPack:
    return ReviewPack(
        diff=DIFF,
        changed_files=[
            FileMeta(path="a.py", language="python"),
            FileMeta(path="service/auth.py", language="python"),
        ],
        artifact_fingerprint="artifact",
        pack_fingerprint="pack",
        focus=focus,
        budget=PackBudget(max_files=max_files, max_chars_total=max_chars_total),
    )


class TestBudgetGate:
    def test_complete_without_limits(self):
        result = apply_budget_gate(_pack())
        assert result.status == BudgetStatus.COMPLETE
        assert result.files_reviewed == 2
        assert result.files_total == 2
        assert result.effective_pack is not None
        assert len(result.effective_pack.changed_files) == 2

    def test_focus_priority_applies_before_diff_order(self):
        result = apply_budget_gate(_pack(max_files=1, focus=["auth"]))
        assert result.status == BudgetStatus.TRUNCATED
        assert result.effective_pack is not None
        assert [item.path for item in result.effective_pack.changed_files] == ["service/auth.py"]

    def test_first_file_forced_in_even_when_soft_char_limit_exceeded(self):
        result = apply_budget_gate(_pack(max_chars_total=10))
        assert result.status == BudgetStatus.TRUNCATED
        assert result.files_reviewed == 1
        assert result.chars_consumed > result.chars_limit

    def test_rejected_when_first_file_breaches_absolute_hard_cap(self, monkeypatch):
        monkeypatch.setattr("change_audit.review.budget.ABSOLUTE_MAX_FIRST_FILE_CHARS", 20)
        result = apply_budget_gate(_pack())
        assert result.status == BudgetStatus.REJECTED
        assert result.effective_pack is None

    def test_invalid_pack_shape_rejected(self):
        pack = ReviewPack(
            diff="not a unified diff\n",
            changed_files=[FileMeta(path="a.py")],
            artifact_fingerprint="artifact",
            pack_fingerprint="pack",
        )
        result = apply_budget_gate(pack)
        assert result.status == BudgetStatus.REJECTED

    def test_diff_chunk_mapping_uses_paths_not_changed_file_index(self):
        pack = ReviewPack(
            diff=DIFF,
            changed_files=[
                FileMeta(path="service/auth.py", language="python"),
                FileMeta(path="a.py", language="python"),
            ],
            artifact_fingerprint="artifact",
            pack_fingerprint="pack",
            focus=["auth"],
            budget=PackBudget(max_files=1),
        )
        result = apply_budget_gate(pack)
        assert result.status == BudgetStatus.TRUNCATED
        assert result.effective_pack is not None
        assert [item.path for item in result.effective_pack.changed_files] == ["service/auth.py"]
        assert "diff --git a/service/auth.py b/service/auth.py" in result.effective_pack.diff
