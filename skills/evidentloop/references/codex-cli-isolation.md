# Codex CLI isolation profile

Use this profile only for the verified Codex CLI path. It maps the host-neutral isolation contract in [SKILL.md](../SKILL.md) to Codex CLI controls. It does not define requirements for other hosts.

This profile is verified with Codex CLI `0.144.1` and `0.144.3`. An ordinary collaboration subagent or a claim that the context is fresh is not evidence of isolation.

1. Record the orchestrator's `thread.started` ID.
2. Create a fresh writable HOME, empty working directory, and writable ephemeral `CODEX_HOME`. Copy only `auth.json` from the authenticated Codex directory into the ephemeral `CODEX_HOME`, keep both directories mode `0700` and the copied file mode `0600`, and never print its contents. This file is transport authentication only; the reviewer still has no file or tool access.
3. Start a separate `codex exec` process with only the complete prompt as its user input. On macOS, pass the system CA file when the host transport requires it:

```text
HOME=<EMPTY_HOME> CODEX_HOME=<EPHEMERAL_CODEX_HOME> \
SSL_CERT_FILE=<SYSTEM_CA_FILE> \
codex -a never exec --ephemeral --ignore-user-config --ignore-rules --strict-config \
  --skip-git-repo-check -C <EMPTY_DIRECTORY> -s read-only \
  -c 'tools={}' -c 'mcp_servers={}' \
  -c 'shell_environment_policy.inherit="none"' \
  --disable shell_tool --disable unified_exec --disable code_mode_host \
  --disable browser_use --disable browser_use_external \
  --disable browser_use_full_cdp_access --disable in_app_browser \
  --disable computer_use --disable apps --disable enable_mcp_apps \
  --disable plugins --disable plugin_sharing --disable hooks \
  --disable image_generation --disable workspace_dependencies \
  --disable multi_agent --disable goals --disable auth_elicitation \
  --disable request_permissions_tool --disable tool_suggest \
  --json <PROMPT_TEXT>
```

Pass `<PROMPT_TEXT>` as one argv value, not shell source. Before invoking `finalize`, compare and assert a non-empty reviewer `thread.started` ID different from the orchestrator ID; a comparison performed after `finalize` does not satisfy this gate. Also require exactly one final `agent_message` and `turn.completed`. Reject the run if JSONL contains any tool item or `command_execution`, `file_change`, or `collab_tool_call` event, or if the empty working directory changes. Remove the temporary HOME, `CODEX_HOME`, and working directory before `finalize`; a cleanup failure is a blocker. Write only the final `agent_message` text unchanged to `raw_analysis_path`. Invoke `finalize` only after all pre-finalize assertions and cleanup pass. If any check fails, stop before `finalize`.
