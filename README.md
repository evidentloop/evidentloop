<h1 align="center">EvidentLoop</h1>

<p align="center"><strong>Turn local Git diffs into evidence-backed, traceable audit reports.</strong></p>

<p align="center">
  <a href="https://github.com/evidentloop/evidentloop/blob/main/README.md">English</a> ·
  <a href="https://github.com/evidentloop/evidentloop/blob/main/README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <img alt="Status: Alpha" src="https://img.shields.io/badge/status-alpha-F59E0B">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776AB">
  <img alt="Code-diff schema 0.4" src="https://img.shields.io/badge/code--diff%20schema-0.4-0F766E">
</p>

![EvidentLoop product path from Git diff to human decisions](https://raw.githubusercontent.com/evidentloop/evidentloop/v0.1.0a1/docs/assets/evidentloop-cover.png)

EvidentLoop turns a local Git diff into a single HTML report. Any finding included in the risk score is tied to a real changed line, so you can verify it, record a decision, and ask your coding agent to update the same report without re-reviewing or changing code.

The Alpha report UI and review text are Simplified Chinese.

## Quick start

Requirements: Git, Python 3.10 or newer, uv, Node.js/npx for Skill installation, and a coding agent with Skill support.

```bash
# Try the offline demo
uvx evidentloop demo

# Install the CLI and Skill
uv tool install evidentloop
npx skills@latest add evidentloop/evidentloop --skill evidentloop -g
evidentloop doctor
```

`pipx install evidentloop` is the CLI fallback.

Inside the Git repository to inspect, ask your coding agent:

```text
Use EvidentLoop to audit my staged changes and generate the HTML report.
```

## Output

| File | Purpose |
|---|---|
| `audit.json` | Validated audit record linking Git changes to findings. |
| `audit.html` | Single-file report showing the relevant diff and browser-local decisions. |
| `audit-feedback.jsonl` | Optional machine-readable decision export; the report's primary action copies the same payload for a coding agent. |

| Schema 0.4 report overview | Human adjudication and copy-to-AI flow |
|---|---|
| [![Schema 0.4 report overview](https://raw.githubusercontent.com/evidentloop/evidentloop/v0.1.0a1/docs/assets/evidentloop-report-overview.png)](https://raw.githubusercontent.com/evidentloop/evidentloop/v0.1.0a1/docs/assets/evidentloop-report-overview.png) | [![Human adjudication and copy-to-AI flow](https://raw.githubusercontent.com/evidentloop/evidentloop/v0.1.0a1/docs/assets/evidentloop-report-feedback.png)](https://raw.githubusercontent.com/evidentloop/evidentloop/v0.1.0a1/docs/assets/evidentloop-report-feedback.png) |

Open the HTML locally, or publish a redacted copy to static hosting. Pending feedback stays in each viewer's browser until copied or downloaded; the report is shareable, but it is not a multi-user review service.

After recording decisions, click **复制给 AI 更新报告** (“Copy for AI to update report”). In the workspace that contains the original `audit.json`, paste the block into an EvidentLoop-enabled coding agent. By default, `revise` updates only `audit.json` and `audit.html` in the same directory; other files stay untouched. Explicit `--out` creates a new copy. Stale, conflicting, or ambiguous feedback stops without guessing; report revision never modifies business code or invokes model review.

EvidentLoop uses the model already available in your coding agent. It never executes commands found in the diff or model output.

## How it works

[![EvidentLoop architecture from host review to validated artifact pair](https://raw.githubusercontent.com/evidentloop/evidentloop/v0.1.0a1/docs/assets/evidentloop-architecture.png)](https://raw.githubusercontent.com/evidentloop/evidentloop/v0.1.0a1/docs/assets/evidentloop-architecture.png)

`complete` means the host returned a valid, complete result. What it finds still depends on the host model and the context it received.

## Alpha scope

| Supported | Not supported |
|---|---|
| Local Git staged, unstaged, ref, and range diffs | Folder diff, file-only review, or remote PR URLs |
| Added, modified, deleted, renamed, and binary-file metadata | Automatic fixes or command execution |
| Schema `0.4`, report revision, exact changed-line evidence | Automatic fixes or model re-review from feedback |
| In-place feedback revision with paired JSON/HTML rollback and explicit copy output | Automatic stale-feedback merging or cross-workspace report search |
| Complete, partial, failed, and inconclusive states | Review targets other than Git diffs |

## Integration and development

Most users should use the Skill. Host integrators can use the `prepare -> external review -> finalize` path documented in [AI host integration](https://github.com/evidentloop/evidentloop/blob/main/docs/ai-host-integration.md). The public Python API is available from `evidentloop.api`.

For local development:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m ruff check .
python -m build
```

References: [Pages and sample report](https://evidentloop.github.io/evidentloop/) · [V0 scope](https://github.com/evidentloop/evidentloop/blob/main/docs/v0-scope.md) · [Data model](https://github.com/evidentloop/evidentloop/blob/main/docs/data-model.md) · [AI host integration](https://github.com/evidentloop/evidentloop/blob/main/docs/ai-host-integration.md)

Alpha feedback and bug reports are welcome in [GitHub Issues](https://github.com/evidentloop/evidentloop/issues).

## License

Licensed under the [MIT License](https://github.com/evidentloop/evidentloop/blob/main/LICENSE).
