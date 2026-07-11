"""Tests for crossreview render-prompt and ingest CLI commands."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from change_audit.review.cli import main
from change_audit.review.pack import assemble_pack, pack_to_json
from change_audit.review.schema import FileMeta


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

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

**f-001**
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


def _write_pack(tmp_path: Path, **kwargs) -> Path:
    pack = assemble_pack(
        SAMPLE_DIFF,
        changed_files=SAMPLE_FILES,
        **kwargs,
    )
    path = tmp_path / "pack.json"
    path.write_text(pack_to_json(pack), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# render-prompt
# ---------------------------------------------------------------------------

class TestRenderPromptCLI:
    """crossreview render-prompt CLI."""

    def test_basic_render(self, capsys, tmp_path):
        pack_path = _write_pack(tmp_path, intent="fix greeting")
        rc = main(["render-prompt", "--pack", str(pack_path)])
        assert rc == 0
        out = capsys.readouterr()
        # Output should contain the rendered prompt with diff content
        assert "print(\"hello\")" in out.out
        assert "print(\"world\")" in out.out
        # Should contain the intent
        assert "fix greeting" in out.out
        # Diagnostic on stderr
        assert "crossreview render-prompt:" in out.err
        assert "chars" in out.err
        assert "template=product/v0.2" in out.err

    def test_render_contains_changed_files(self, capsys, tmp_path):
        pack_path = _write_pack(tmp_path)
        rc = main(["render-prompt", "--pack", str(pack_path)])
        assert rc == 0
        out = capsys.readouterr()
        assert "hello.py" in out.out

    def test_render_with_custom_template(self, capsys, tmp_path):
        pack_path = _write_pack(tmp_path, intent="test intent")
        template = tmp_path / "custom.md"
        template.write_text(
            "CUSTOM TEMPLATE\nIntent: {intent}\nDiff:\n{diff}\n"
            "Task: {task_file}\nFocus: {focus}\n"
            "Changed: {changed_files}\nContext: {context_files}\n"
            "Evidence: {evidence}\n",
            encoding="utf-8",
        )
        rc = main(["render-prompt", "--pack", str(pack_path), "--template", str(template)])
        assert rc == 0
        out = capsys.readouterr()
        assert "CUSTOM TEMPLATE" in out.out
        assert "test intent" in out.out
        assert str(template) in out.err

    def test_render_invalid_pack(self, capsys, tmp_path):
        pack_path = tmp_path / "bad.json"
        pack_path.write_text("{not json", encoding="utf-8")
        rc = main(["render-prompt", "--pack", str(pack_path)])
        assert rc == 1
        assert "not valid JSON" in capsys.readouterr().err

    def test_render_missing_pack(self, capsys):
        rc = main(["render-prompt", "--pack", "/nonexistent/pack.json"])
        assert rc == 1
        assert "cannot read pack file" in capsys.readouterr().err

    def test_render_missing_template(self, capsys, tmp_path):
        pack_path = _write_pack(tmp_path)
        rc = main(["render-prompt", "--pack", str(pack_path), "--template", "/nonexistent/t.md"])
        assert rc == 1
        assert "cannot read template file" in capsys.readouterr().err

    def test_render_invalid_pack_structure(self, capsys, tmp_path):
        pack_path = tmp_path / "pack.json"
        pack_path.write_text(json.dumps({"schema_version": "0.1-alpha"}), encoding="utf-8")
        rc = main(["render-prompt", "--pack", str(pack_path)])
        assert rc == 1
        assert "invalid ReviewPack" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# ingest
# ---------------------------------------------------------------------------

class TestIngestCLI:
    """crossreview ingest CLI."""

    def test_basic_ingest(self, capsys, tmp_path):
        pack_path = _write_pack(tmp_path, intent="fix greeting")
        raw_path = tmp_path / "raw.md"
        raw_path.write_text(SAMPLE_RAW_ANALYSIS, encoding="utf-8")

        rc = main([
            "ingest",
            "--raw-analysis", str(raw_path),
            "--pack", str(pack_path),
            "--model", "claude-sonnet-4-20250514",
        ])
        assert rc == 0
        out = capsys.readouterr()
        parsed = json.loads(out.out)

        # ReviewResult structure
        assert parsed["review_status"] == "complete"
        assert parsed["reviewer"]["model"] == "claude-sonnet-4-20250514"
        assert parsed["reviewer"]["type"] == "fresh_llm"
        assert parsed["reviewer"]["session_isolated"] is True
        assert len(parsed["findings"]) >= 1
        assert parsed["findings"][0]["id"] == "f-001"

        # Budget fields populated correctly
        assert parsed["budget"]["status"] == "complete"
        assert parsed["budget"]["files_reviewed"] == 1
        assert parsed["budget"]["files_total"] == 1
        assert parsed["budget"]["chars_consumed"] == len(SAMPLE_DIFF)

        # Diagnostic on stderr
        assert "crossreview ingest:" in out.err

    def test_ingest_with_metadata(self, capsys, tmp_path):
        pack_path = _write_pack(tmp_path)
        raw_path = tmp_path / "raw.md"
        raw_path.write_text(SAMPLE_RAW_ANALYSIS, encoding="utf-8")

        rc = main([
            "ingest",
            "--raw-analysis", str(raw_path),
            "--pack", str(pack_path),
            "--model", "host_unknown",
            "--prompt-source", "product",
            "--prompt-version", "v0.1",
            "--latency-sec", "2.5",
            "--input-tokens", "1000",
            "--output-tokens", "500",
        ])
        assert rc == 0
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["reviewer"]["model"] == "host_unknown"
        assert parsed["reviewer"]["prompt_source"] == "product"
        assert parsed["reviewer"]["prompt_version"] == "v0.1"
        assert parsed["reviewer"]["latency_sec"] == 2.5
        assert parsed["reviewer"]["input_tokens"] == 1000
        assert parsed["reviewer"]["output_tokens"] == 500

    def test_ingest_stdin(self, capsys, tmp_path):
        pack_path = _write_pack(tmp_path)

        with patch("sys.stdin", new=StringIO(SAMPLE_RAW_ANALYSIS)):
            rc = main([
                "ingest",
                "--raw-analysis", "-",
                "--pack", str(pack_path),
                "--model", "test-model",
            ])
        assert rc == 0
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["review_status"] == "complete"
        assert len(parsed["findings"]) >= 1

    def test_ingest_empty_analysis(self, capsys, tmp_path):
        pack_path = _write_pack(tmp_path)
        raw_path = tmp_path / "raw.md"
        raw_path.write_text("   \n  \n", encoding="utf-8")

        rc = main([
            "ingest",
            "--raw-analysis", str(raw_path),
            "--pack", str(pack_path),
            "--model", "test-model",
        ])
        assert rc == 1
        assert "empty" in capsys.readouterr().err

    def test_ingest_missing_raw_analysis(self, capsys, tmp_path):
        pack_path = _write_pack(tmp_path)
        rc = main([
            "ingest",
            "--raw-analysis", "/nonexistent/raw.md",
            "--pack", str(pack_path),
            "--model", "test-model",
        ])
        assert rc == 1
        assert "cannot read raw analysis file" in capsys.readouterr().err

    def test_ingest_invalid_pack(self, capsys, tmp_path):
        raw_path = tmp_path / "raw.md"
        raw_path.write_text(SAMPLE_RAW_ANALYSIS, encoding="utf-8")
        pack_path = tmp_path / "pack.json"
        pack_path.write_text("{bad json", encoding="utf-8")

        rc = main([
            "ingest",
            "--raw-analysis", str(raw_path),
            "--pack", str(pack_path),
            "--model", "test-model",
        ])
        assert rc == 1

    def test_ingest_raw_analysis_preserved(self, capsys, tmp_path):
        """raw_analysis should be preserved in ReviewResult for audit trail."""
        pack_path = _write_pack(tmp_path)
        raw_path = tmp_path / "raw.md"
        raw_path.write_text(SAMPLE_RAW_ANALYSIS, encoding="utf-8")

        rc = main([
            "ingest",
            "--raw-analysis", str(raw_path),
            "--pack", str(pack_path),
            "--model", "test-model",
        ])
        assert rc == 0
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["reviewer"]["raw_analysis"] == SAMPLE_RAW_ANALYSIS

    def test_ingest_no_findings_analysis(self, capsys, tmp_path):
        """Analysis with no findings should produce empty findings + proper verdict."""
        pack_path = _write_pack(tmp_path, intent="fix greeting")
        raw_path = tmp_path / "raw.md"
        raw_path.write_text(
            "## Section 1: Findings\n\nNo issues found.\n\n"
            "## Section 2: Observations\n\nLooks good.\n",
            encoding="utf-8",
        )

        rc = main([
            "ingest",
            "--raw-analysis", str(raw_path),
            "--pack", str(pack_path),
            "--model", "test-model",
        ])
        assert rc == 0
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["findings"] == []
        assert parsed["review_status"] == "complete"


# ---------------------------------------------------------------------------
# ingest core module
# ---------------------------------------------------------------------------

class TestRunIngest:
    """change_audit.review.ingest.run_ingest unit tests."""

    def test_run_ingest_produces_valid_result(self):
        from change_audit.review.ingest import run_ingest
        from change_audit.review.schema import validate_review_result

        pack = assemble_pack(SAMPLE_DIFF, changed_files=SAMPLE_FILES, intent="test")
        result = run_ingest(
            pack,
            SAMPLE_RAW_ANALYSIS,
            model="test-model",
            prompt_source="product",
            prompt_version="v0.1",
        )

        violations = validate_review_result(result)
        assert not violations, f"ReviewResult validation failed: {violations}"
        assert result.review_status.value == "complete"
        assert result.reviewer.model == "test-model"
        assert result.reviewer.prompt_source == "product"
        assert result.budget.status.value == "complete"
        assert result.budget.files_reviewed == 1
        assert result.budget.files_total == 1
        assert result.budget.chars_consumed == len(SAMPLE_DIFF)

    def test_run_ingest_budget_chars_limit(self):
        from change_audit.review.ingest import run_ingest
        from change_audit.review.schema import PackBudget

        pack = assemble_pack(
            SAMPLE_DIFF,
            changed_files=SAMPLE_FILES,
            budget=PackBudget(max_chars_total=50000),
        )
        result = run_ingest(pack, SAMPLE_RAW_ANALYSIS, model="m")
        assert result.budget.chars_limit == 50000
