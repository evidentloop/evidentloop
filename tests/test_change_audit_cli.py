"""Public module CLI tests."""

from __future__ import annotations

import json
from pathlib import Path

from change_audit.cli import main
from tests.audit_helpers import minimal_audit


def test_render_command_writes_html(tmp_path: Path, capsys) -> None:
    source = tmp_path / "audit.json"
    target = tmp_path / "audit.html"
    source.write_text(json.dumps(minimal_audit()), encoding="utf-8")
    assert main(["render", str(source), "--out", str(target)]) == 0
    assert capsys.readouterr().out.strip() == str(target)
    assert target.is_file()


def test_render_command_reports_validation_error(tmp_path: Path, capsys) -> None:
    source = tmp_path / "audit.json"
    source.write_text("{}", encoding="utf-8")
    assert main(["render", str(source), "--out", str(tmp_path / "audit.html")]) == 1
    assert "change-audit render:" in capsys.readouterr().err
