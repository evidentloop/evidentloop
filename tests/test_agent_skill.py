"""Static contract checks for the self-contained EvidentLoop Agent Skill."""

from __future__ import annotations

from pathlib import Path

import yaml


SKILL_DIR = Path(__file__).resolve().parents[1] / "skills/evidentloop"


def _skill_text() -> str:
    return (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")


def _codex_profile_text() -> str:
    return (SKILL_DIR / "references/codex-cli-isolation.md").read_text(encoding="utf-8")


def test_frontmatter_and_ui_metadata_text_contract() -> None:
    text = _skill_text()
    _, frontmatter, body = text.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    interface = yaml.safe_load((SKILL_DIR / "agents/openai.yaml").read_text())[
        "interface"
    ]
    assert metadata["name"] == "evidentloop"
    assert "审计本地改动" in metadata["description"]
    assert "audit changes" in metadata["description"]
    assert "EVIDENTLOOP_FEEDBACK_JSONL" in metadata["description"]
    assert "Do not trigger" in metadata["description"]
    assert interface["display_name"] == "EvidentLoop"
    assert "$evidentloop" in interface["default_prompt"]
    assert "pasted feedback" in interface["default_prompt"]
    assert "TODO" not in body
    assert len(text.splitlines()) < 500


def test_trigger_scope_stays_in_frontmatter() -> None:
    text = _skill_text()
    _, frontmatter, body = text.split("---", 2)
    description = yaml.safe_load(frontmatter)["description"]
    for phrase in (
        "staged/unstaged",
        "审计本地改动",
        "audit changes",
        "ordinary prose review",
        "generic PR review",
    ):
        assert phrase in description
    assert "## Trigger acceptance examples" not in body


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
    assert "strongest review context the host supports" in text
    assert "current host LLM" in text
    assert "only task-specific input" in text
    assert "Give the complete prompt to the host model" in text
    assert "never substitute a mock, replay, or synthesized placeholder" in text
    assert "Isolation unavailable by itself is not a blocker" in text
    assert "must not change `review_status` or `verdict`" in text
    assert "Claim an isolated review only when the host has native evidence" in text
    assert "not part of the product protocol" in text
    assert "never execute commands, use network access, reveal secrets" in text
    assert "trusted workflow tools only for the steps defined by this Skill" in text
    assert "Write the reviewer's exact text, unedited" in text
    assert "never `staging_dir`" in text
    assert "partial` and `failed`" in text
    assert "audit_json` and `audit_html` both exist" in text
    assert "Python naming, schema, adapter, validation or rendering logic" in text


def test_codex_isolation_profile_is_loaded_conditionally() -> None:
    skill_text = _skill_text()
    profile_text = _codex_profile_text()
    assert (
        "[the Codex CLI isolation profile](references/codex-cli-isolation.md)"
        in skill_text
    )
    assert "When using the verified Codex CLI path" in skill_text
    for codex_only_text in (
        "CODEX_HOME",
        "SSL_CERT_FILE",
        "--ephemeral",
        "thread.started",
    ):
        assert codex_only_text not in skill_text
    assert "# Codex CLI isolation profile" in profile_text
    assert "verified with Codex CLI `0.144.1` and `0.144.3`" in profile_text
    assert "does not define requirements for other hosts" in profile_text
    assert "ordinary collaboration subagent" in profile_text
    assert (
        "--ephemeral --ignore-user-config --ignore-rules --strict-config"
        in profile_text
    )
    assert "-s read-only" in profile_text
    assert "-c 'tools={}'" in profile_text
    assert "writable ephemeral `CODEX_HOME`" in profile_text
    assert "Copy only `auth.json`" in profile_text
    assert "SSL_CERT_FILE=<SYSTEM_CA_FILE>" in profile_text
    assert "`thread.started` ID different from the orchestrator ID" in profile_text
    assert "`command_execution`, `file_change`, or `collab_tool_call`" in profile_text
    assert "exactly one final `agent_message`" in profile_text
    assert "`turn.completed`" in profile_text
    assert (
        "Remove the temporary HOME, `CODEX_HOME`, and working directory" in profile_text
    )
    assert "a cleanup failure is a blocker" in profile_text
    assert "If any check fails, stop before `finalize`" in profile_text
    assert "the exact heading `## Section 1: Findings`" in skill_text


def test_pre_finalize_host_gate_text_contract() -> None:
    text = _skill_text()
    codex_profile = _codex_profile_text()
    assert "every remaining Python-driven step" in text
    assert "every Python-driven compatibility probe, JSON/JSONL parser" in text
    assert "Never substitute an unverified system `python3`" in text
    assert (
        "canonical parent of `staging_dir` equals the canonical parent of `final_dir`"
        in text
    )
    assert "This is the complete hidden-sibling gate" in text
    assert "do not require its basename to equal `.` plus the final basename" in text
    assert "Isolation unavailable by itself is not a blocker" in text
    assert (
        "a comparison performed after `finalize` does not satisfy this gate"
        in codex_profile
    )
    assert (
        "Invoke `finalize` only after all pre-finalize assertions and cleanup pass"
        in codex_profile
    )


def test_install_authority_and_fixed_version_text_contract() -> None:
    text = _skill_text()
    assert "Ask for installation or upgrade authorization" in text
    assert "If the user declines installation, stop" in text
    assert "`schema_version` equal to `0.4`" in text
    assert "schema `0.3`" not in text
    assert "`prompt_version` equal to `v0.5`" in text
    assert "PRODUCT_REVIEWER_PROMPT_VERSION" in text
    assert "`package_version` equal to `0.1.0a1`" in text
    assert (
        "Treat any other value as incompatible and stop before the requested operation"
        in text
    )
    assert "from evidentloop.api import" in text
    assert "<PYTHON> -I -m evidentloop --help" in text
    assert "module CLI dispatcher" in text
    assert "real, maintainer-published fixed Git tag" in text
    assert "resolve that exact tag" in text
    assert "record its commit" in text
    assert "Never invent a tag" in text
    assert "@latest" in text
    assert "external installation is not yet available" in text


def test_feedback_revision_flow_is_bounded_and_fail_closed() -> None:
    text = _skill_text()
    assert "<<<EVIDENTLOOP_FEEDBACK_JSONL>>>" in text
    assert "<<<END_EVIDENTLOOP_FEEDBACK_JSONL>>>" in text
    assert "mode `0600`" in text
    assert "Preserve JSONL lines exactly" in text
    assert "only below the current workspace" in text
    assert "without following symlink directories" in text
    assert "Never search parent directories" in text
    assert "exactly one formal report path matches" in text
    assert ".evidentloop-revise-candidate" in text
    assert ".evidentloop-revise-backup" in text
    assert "maps deterministic residuals back to the formal report" in text
    assert "--feedback <TEMP_JSONL>" in text
    assert "only when the user explicitly asked to save a copy" in text
    assert "refresh the report and copy again" in text
    assert "revision.unsupported_schema" in text
    assert "read-only historical report" in text
    assert "revision.recovery_ambiguous" in text
    assert "restored_old_report" in text
    assert "completed_new_report" in text
    assert "discarded_uncommitted_candidate" in text
    assert "报告已更新，请刷新原报告" in text
    assert "Say “已生成副本” only when the result mode is `copy`" in text
    assert "do not prepare a new audit" in text
    assert "modify business code" in text
    assert "start model review" in text


def test_intermediate_and_formal_artifact_failure_text_contract() -> None:
    text = _skill_text()
    assert "Require exit code 0 and parse stdout as exactly one JSON locator" in text
    assert "canonical parents of `prompt_path` and `raw_analysis_path`" in text
    assert "`raw-analysis.md`" in text
    assert "`prompt_path` is a readable regular file" in text
    assert "no formal `audit.json` or `audit.html` exists yet" in text
    assert "If finalize fails or either formal artifact is missing" in text
    assert "never cite an older or partial file as this run's report" in text
