"""Static contract checks for the self-contained EvidentLoop Agent Skill."""

from __future__ import annotations

from pathlib import Path

import yaml


SKILL_DIR = Path(__file__).resolve().parents[1] / "skills/evidentloop"


def _skill_text() -> str:
    return (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def test_frontmatter_and_ui_metadata_text_contract() -> None:
    text = _skill_text()
    _, frontmatter, body = text.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    interface = yaml.safe_load((SKILL_DIR / "agents/openai.yaml").read_text())["interface"]
    assert metadata["name"] == "evidentloop"
    assert "审计本地改动" in metadata["description"]
    assert "audit changes" in metadata["description"]
    assert "Do not trigger" in metadata["description"]
    assert interface["display_name"] == "EvidentLoop"
    assert "$evidentloop" in interface["default_prompt"]
    assert "TODO" not in body
    assert len(text.splitlines()) < 500


def test_positive_and_negative_trigger_examples_text_contract() -> None:
    text = _skill_text()
    for phrase in (
        "帮我用 evidentloop 审计最近的本地改动",
        "审计 staged changes",
        "Use evidentloop to audit",
        "Review this local diff with evidentloop",
    ):
        assert phrase in text
    for phrase in (
        "帮我润色这份 review 文档",
        "解释一下这个函数",
        "review this paragraph for grammar",
        "summarize the PR discussion",
    ):
        assert phrase in text


def test_host_security_and_public_command_text_contract() -> None:
    text = _skill_text()
    assert "resolve `evidentloop`" in text
    assert "`doctor --json`" in text
    assert "`python_executable`" in text
    assert "absolute console-script path" in text
    assert "canonical target" in text
    assert "never its canonical target" in text
    assert "removes `PYTHONPATH` and `PYTHONHOME`" in text
    assert "`PYTHONNOUSERSITE=1`" in text
    assert "Never search the filesystem" in text
    assert "controlled fixed-wheel trial" in text
    assert "<PYTHON> -I -c" in text
    assert "<PYTHON> -I -m evidentloop prepare --diff <SPEC>" in text
    assert "<PYTHON> -I -m evidentloop finalize --out <LOCATOR_FINAL_DIR>" in text
    assert "Never let the reviewer write `audit.json`" in text
    assert "single argv values" in text
    assert "native one-argument quoting" in text
    assert "never concatenate or interpolate raw user-controlled text" in text
    assert "fresh isolated reviewer context" in text
    assert "Do not grant the reviewer shell execution" in text
    assert "Write the reviewer's exact text, unedited" in text
    assert "never `staging_dir`" in text
    assert "partial` and `failed`" in text
    assert "audit_json` and `audit_html` both exist" in text
    assert "Python naming, schema, adapter, validation or rendering logic" in text


def test_codex_isolation_recipe_text_contract() -> None:
    text = _skill_text()
    assert "Codex CLI 0.144.1 isolation recipe" in text
    assert "ordinary collaboration subagent" in text
    assert "--ephemeral --ignore-user-config --ignore-rules --strict-config" in text
    assert "-s read-only" in text
    assert "-c 'tools={}'" in text
    assert "writable ephemeral `CODEX_HOME`" in text
    assert "Copy only `auth.json`" in text
    assert "SSL_CERT_FILE=<SYSTEM_CA_FILE>" in text
    assert "`thread.started` ID different from the orchestrator ID" in text
    assert "`command_execution`, `file_change`, or `collab_tool_call`" in text
    assert "exactly one final `agent_message`" in text
    assert "`turn.completed`" in text
    assert "Remove the temporary HOME, `CODEX_HOME`, and working directory" in text
    assert "a cleanup failure is a blocker" in text
    assert "If any check fails, stop before `finalize`" in text
    assert "the exact heading `## Section 1: Findings`" in text


def test_install_authority_and_fixed_version_text_contract() -> None:
    text = _skill_text()
    assert "Ask for installation or upgrade authorization" in text
    assert "If the user declines installation, stop" in text
    assert "`schema_version` equal to `0.3`" in text
    assert "`prompt_version` equal to `v0.4`" in text
    assert "PRODUCT_REVIEWER_PROMPT_VERSION" in text
    assert "`package_version` equal to `0.1.0a0`" in text
    assert "Treat any other value as incompatible and stop before `prepare`" in text
    assert "from evidentloop.api import" in text
    assert "<PYTHON> -I -m evidentloop --help" in text
    assert "module CLI dispatcher" in text
    assert "real, maintainer-published fixed Git tag" in text
    assert "resolve that exact tag" in text
    assert "record its commit" in text
    assert "Never invent a tag" in text
    assert "@latest" in text
    assert "external installation is not yet available" in text


def test_intermediate_and_formal_artifact_failure_text_contract() -> None:
    text = _skill_text()
    assert "Require exit code 0 and parse stdout as exactly one JSON locator" in text
    assert "canonical parents of `prompt_path` and `raw_analysis_path`" in text
    assert "`raw-analysis.md`" in text
    assert "`prompt_path` is a readable regular file" in text
    assert "no formal `audit.json` or `audit.html` exists yet" in text
    assert "If finalize fails or either formal artifact is missing" in text
    assert "never cite an older or partial file as this run's report" in text
