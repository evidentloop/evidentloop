"""Execute the feedback state/export contract in Node when available."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def test_feedback_state_and_jsonl_behavior() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is not available for JavaScript behavior verification")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [node, str(root / "tests/js/audit-feedback.test.cjs")],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "audit feedback behavior: PASS" in result.stdout
