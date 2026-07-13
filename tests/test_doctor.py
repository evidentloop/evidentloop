"""Doctor command contract and failure-boundary tests."""

from __future__ import annotations

import json
from types import SimpleNamespace

import evidentloop.doctor as doctor
from evidentloop.cli import main


def _fake_which(command: str) -> str | None:
    return "/usr/bin/git" if command == "git" else None


def test_doctor_json_keeps_missing_npx_non_blocking(monkeypatch, capsys) -> None:
    monkeypatch.setattr(doctor.shutil, "which", _fake_which)
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="git version 2.50.0\n"),
    )

    assert main(["doctor", "--json"]) == 0

    payload = json.loads(capsys.readouterr().out)
    checks = {item["name"]: item for item in payload["checks"]}
    assert payload["status"] == "warning"
    assert checks["schema"]["status"] == "ok"
    assert checks["prompt"]["status"] == "ok"
    assert checks["package_resources"]["status"] == "ok"
    assert checks["git"]["status"] == "ok"
    assert checks["npx"]["status"] == "warning"
    assert checks["npx"]["blocking"] is False
    assert payload["next_steps"]["skill_install"] == (
        "npx skills@latest add evidentloop/evidentloop --skill evidentloop -g"
    )


def test_doctor_returns_nonzero_for_a_blocking_runtime_failure(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(doctor, "load_audit_schema", lambda: (_ for _ in ()).throw(ValueError("broken schema")))
    monkeypatch.setattr(doctor.shutil, "which", _fake_which)
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="git version 2.50.0\n"),
    )

    assert main(["doctor", "--json"]) == 1

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "error"
    schema = next(item for item in payload["checks"] if item["name"] == "schema")
    assert schema["status"] == "error"
    assert schema["blocking"] is True


def test_doctor_human_output_is_compact(monkeypatch, capsys) -> None:
    monkeypatch.setattr(doctor.shutil, "which", _fake_which)
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="git version 2.50.0\n"),
    )

    assert main(["doctor"]) == 0

    output = capsys.readouterr().out
    assert output.startswith("EvidentLoop doctor: warning\n")
    assert "[WARN] npx:" in output
    assert "Skill install: npx skills@latest add evidentloop/evidentloop" in output
    assert "Then ask: Use EvidentLoop to audit my staged changes" in output
    assert ".codex" not in output
    assert ".config" not in output
