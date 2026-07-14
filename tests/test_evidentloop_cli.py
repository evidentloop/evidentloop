"""Public module CLI tests."""

from __future__ import annotations

import json
from pathlib import Path

from evidentloop.cli import _parser, main
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
    assert "evidentloop render:" in capsys.readouterr().err


def test_module_and_console_help_share_the_evidentloop_program_name() -> None:
    parser = _parser()
    assert parser.prog == "evidentloop"
    assert {action.dest for action in parser._actions} >= {"help", "command"}


def test_demo_command_runs_frozen_replay_and_marks_all_outputs(
    tmp_path: Path,
    capsys,
) -> None:
    output = tmp_path / "demo-report"

    assert main(["demo", "--out", str(output)]) == 0

    captured = capsys.readouterr()
    terminal = json.loads(captured.out)
    assert terminal["execution_mode"] == "demo_replay"
    assert terminal["fixture_id"] == "synthetic-off-by-one-v1"
    assert terminal["live_ai_review"] is False
    assert "no live AI review" in captured.err

    audit_text = (output / "audit.json").read_text(encoding="utf-8")
    audit = json.loads(audit_text)
    provenance = audit["source"]["extensions"]["evidentloop"]
    assert provenance == {
        "execution_mode": "demo_replay",
        "fixture_id": "synthetic-off-by-one-v1",
        "reviewer": "frozen_replay",
        "live_ai_review": False,
    }
    assert "evidentloop-demo-" not in audit_text
    html = (output / "audit.html").read_text(encoding="utf-8")
    assert 'data-demo-provenance="frozen-replay"' in html
    assert "没有执行实时 AI 审查" in html


def test_demo_refuses_to_overwrite_an_existing_output(tmp_path: Path, capsys) -> None:
    output = tmp_path / "existing"
    output.mkdir()

    assert main(["demo", "--out", str(output)]) == 1

    assert "output or staging leaf already exists" in capsys.readouterr().err


def test_demo_ignores_global_git_signing_and_hooks(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    reject = tmp_path / "reject-git-side-effect"
    reject.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    reject.chmod(0o755)
    hooks = tmp_path / "global-hooks"
    hooks.mkdir()
    pre_commit = hooks / "pre-commit"
    pre_commit.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    pre_commit.chmod(0o755)
    global_config = tmp_path / "global.gitconfig"
    global_config.write_text(
        "[commit]\n"
        "\tgpgsign = true\n"
        "[gpg]\n"
        f"\tprogram = {reject}\n"
        "[core]\n"
        f"\thooksPath = {hooks}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")

    output = tmp_path / "isolated-demo"
    assert main(["demo", "--out", str(output)]) == 0

    captured = capsys.readouterr()
    assert json.loads(captured.out)["execution_mode"] == "demo_replay"
