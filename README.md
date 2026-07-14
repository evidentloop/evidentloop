<h1 align="center">EvidentLoop</h1>

<p align="center"><strong>Evidence-grounded review for local Git diffs.</strong></p>

<p align="center">
  <a href="./README.md">English</a> ·
  <a href="./README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <img alt="Status: Alpha" src="https://img.shields.io/badge/status-alpha-F59E0B">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776AB">
  <img alt="Code-diff schema 0.3" src="https://img.shields.io/badge/code--diff%20schema-0.3-0F766E">
</p>

![EvidentLoop cover](./docs/assets/evidentloop-cover.png)

EvidentLoop turns a review of a local Git diff into a validated `audit.json` and a self-contained `audit.html`. A scored finding must resolve to a real changed line. Missing, malformed, or incomplete review output remains visibly incomplete.

> [!IMPORTANT]
> This repository is a local Alpha (`0.1.0a0`) with no PyPI release, release tag, or public Pages site yet. A local checkout install provides the `evidentloop` console script, `doctor`, and an offline synthetic `demo`; `python -m evidentloop` remains equivalent for development and diagnostics.

## Output

| File | Purpose |
|---|---|
| `audit.json` | Canonical, validated audit record with trusted hunks and graph relationships. |
| `audit.html` | Self-contained browser report with bounded code evidence, changed-line highlights, and local decisions. |
| `audit-feedback.jsonl` | Optional export of reviewer decisions. The Alpha records this feedback but does not consume it or edit code. |

The implementation enforces three rules:

- Python checks findings against the prepared Git diff. The semantic reviewer cannot create trusted paths, hunk IDs, fingerprints, or scores.
- JSON and HTML are validated and published as one pair. A hard failure cannot leave a half-report that looks successful.
- `complete` means the reviewer satisfied the output contract. It does not mean every behavioral risk was found.

## Historical reports

The repository keeps three reports generated before the EvidentLoop identity migration:

- [Fireworks Tech Graph `product/v0.3` dogfood](./docs/examples/dogfood-fireworks-tech-graph-v03/)
- [Fireworks Tech Graph `product/v0.2` dogfood](./docs/examples/dogfood-fireworks-tech-graph/)
- [Hunk rendering reference](./docs/examples/hunk-context-demo/)

Their `audit.json` and `audit.html` files retain the original schema `0.2` and product provenance. They are frozen historical evidence, not current schema `0.3` fixtures, and the identity migration does not rewrite them.

## Quick start

Requirements: Git, Python 3.10 or newer, and an AI host that can discover the Skill and ask its model to review the change. EvidentLoop does not bind to a host; compatibility is declared only after a host completes the end-to-end workflow.

### Public Alpha path

The public release will use one short path: view the report at `https://evidentloop.github.io/evidentloop/`, try the offline replay, install the CLI and Skill, run diagnostics, then ask for an audit.

```bash
uvx evidentloop demo
uv tool install evidentloop
npx skills@latest add evidentloop/evidentloop --skill evidentloop -g
evidentloop doctor
```

These commands are the release target, not a claim of current availability. PyPI, the renamed repository, remote Skill installation, and Pages remain unavailable until the release checkpoint is complete. Use `pipx install evidentloop` only as the published CLI fallback.

After release, update or remove the installation with:

```bash
uv tool upgrade evidentloop
npx skills@latest update evidentloop -g
uv tool uninstall evidentloop
npx skills@latest remove evidentloop -g -y
```

For pipx, use `pipx upgrade evidentloop` or `pipx uninstall evidentloop`.

### Current local Alpha

Until the public release, install from this checkout:

```bash
git clone https://github.com/evidentloop/change-audit.git evidentloop
cd evidentloop
python3.11 --version       # any installed Python >=3.10
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
evidentloop doctor
evidentloop demo --out evidentloop-demo
npx skills@latest add . --skill evidentloop --agent codex -g --copy
```

`demo` uses a bundled synthetic Git change and frozen reviewer replay. It does not access a model or the network, and its terminal, JSON, and HTML outputs explicitly mark that provenance.

The final install command above is the verified Codex example; other hosts use their supported Skill installation target. Codex completed the real audit E2E on macOS arm64 with CLI `0.144.1` and `0.144.3`. Host-specific evidence and current compatibility status are recorded in [AI host integration](./docs/ai-host-integration.md).

Then, inside the Git repository to inspect, ask the host:

```text
Use EvidentLoop to audit my staged changes and generate the HTML report.
```

Or in Chinese:

```text
帮我用 EvidentLoop 审计 staged changes，并生成 HTML 报告。
```

The Skill requires package `0.1.0a0`, schema `0.3`, and prompt `v0.5` before `prepare`; any mismatch stops the run. It then prepares a trusted workspace, asks the host model to review the generated prompt, finalizes the report pair, and returns the report paths. When the host can establish and verify a separate review context, the Skill uses it as an isolation enhancement. The current report UI and reviewer prose are Simplified Chinese.

## How it works

```text
natural-language request
  → EvidentLoop Skill resolves repository and diff scope
  → Python prepare freezes Git evidence and prompt provenance
  → host LLM returns semantic findings
  → Python verifies changed-line anchors and builds the Audit Graph
  → schema, semantics, trace links, and HTML pass validation
  → audit.json + audit.html are published together
  → optional browser-local feedback export
```

![EvidentLoop architecture](./docs/assets/evidentloop-architecture.png)

EvidentLoop uses the model capability already supplied by the AI host. It does not require a separate model SDK or API key. Reviewed diffs and model output are untrusted data; commands embedded in either are never executed.

## Host integrator commands

Most users should use the Skill. Integrators can call the module commands directly:

```bash
# 1. Create a hidden staging workspace and print one JSON locator.
python -m evidentloop prepare --diff staged --out audit/20260710_example

# 2. Give the complete locator.prompt_path to the host LLM
#    and write its exact response to locator.raw_analysis_path.

# 3. Validate and publish the report pair. The final directory must not exist.
python -m evidentloop finalize --out audit/20260710_example

# Re-render a current schema 0.3 JSON artifact.
python -m evidentloop render \
  audit/20260710_example/audit.json \
  --out audit/20260710_example/audit.html
```

`review` is a Skill action, not a Python command. `prepare` and `finalize` are not a shortcut pair: the host model's response must be written between them. Mock, replayed, or synthesized placeholder output is not an end-to-end review. Explicit `render --out` replaces only that HTML file and never modifies `audit.json`.

The public Python API is available from `evidentloop.api`:

```python
from evidentloop.api import finalize_review, prepare_local_diff, render_audit_file
```

See [AI host integration](./docs/ai-host-integration.md) for the locator contract, failure handling, prompt boundary, and installation consent rules.

## Current Alpha scope

| Capability | Status |
|---|---|
| Local Git `staged`, `unstaged`, ref, and range diffs | Implemented |
| Added, modified, deleted, renamed, and binary-file metadata | Implemented |
| `code_diff` schema and self-contained HTML | Schema `0.3` |
| Exact add/delete-line anchors and bounded trusted hunks | Implemented |
| Complete, partial, failed, and inconclusive states | Implemented |
| Browser-local decisions and JSONL export | Implemented; not consumed |
| Report language | Simplified Chinese |
| Folder diff, file-only review, or remote PR URL | Not supported |
| Console script, `doctor`, and offline synthetic replay `demo` | Implemented locally; not published to PyPI |
| Automatic fixes, command execution, or feedback ingestion | Not supported in the first public Alpha |
| PyPI, release tag, or public Pages | Not available |
| Standard Skill installation | Local checkout and Codex E2E verified; Qoder mechanical path trialed, host review E2E pending; remote release install unavailable |

The current public audit target is a Git diff. Additional artifact profiles require their own adapter, trusted anchors, evaluation baseline, and renderer contract before they can become supported review targets.

## Development

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
python -m ruff check .
python -m build
```

References:

- [V0 scope](./docs/v0-scope.md)
- [Data model](./docs/data-model.md)
- [AI host integration](./docs/ai-host-integration.md)
- [External Alpha trial checklist](./docs/alpha-trial.md)

## License

Licensed under the [MIT License](./LICENSE).
