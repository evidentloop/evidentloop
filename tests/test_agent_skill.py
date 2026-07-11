"""Static contract checks for the self-contained change-audit Agent Skill."""

from __future__ import annotations

from pathlib import Path

import yaml


SKILL_DIR = Path(__file__).resolve().parents[1] / "integrations/agent-skill/change-audit"


def _skill_text() -> str:
    return (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def test_frontmatter_and_ui_metadata_text_contract() -> None:
    text = _skill_text()
    _, frontmatter, body = text.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    interface = yaml.safe_load((SKILL_DIR / "agents/openai.yaml").read_text())["interface"]
    assert metadata["name"] == "change-audit"
    assert "审计本地改动" in metadata["description"]
    assert "audit changes" in metadata["description"]
    assert "Do not trigger" in metadata["description"]
    assert interface["display_name"] == "Change Audit"
    assert "$change-audit" in interface["default_prompt"]
    assert "TODO" not in body
    assert len(text.splitlines()) < 500


def test_positive_and_negative_trigger_examples_text_contract() -> None:
    text = _skill_text()
    for phrase in (
        "帮我用 change-audit 审计最近的本地改动",
        "审计 staged changes",
        "Use change-audit to audit",
        "Review this local diff with change-audit",
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
    assert "<PYTHON> -m change_audit prepare --diff <SPEC>" in text
    assert "<PYTHON> -m change_audit finalize --out <LOCATOR_FINAL_DIR>" in text
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


def test_install_authority_and_fixed_version_text_contract() -> None:
    text = _skill_text()
    assert "Ask for installation or upgrade authorization" in text
    assert "If the user declines installation, stop" in text
    assert "`schema_version` equal to `0.2`" in text
    assert "non-empty `package_version`" in text
    assert "from change_audit.api import" in text
    assert "<PYTHON> -m change_audit --help" in text
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
