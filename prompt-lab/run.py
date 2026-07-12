#!/usr/bin/env python3
"""Render the canonical EvidentLoop reviewer prompt for a saved case.

Usage:
    python prompt-lab/run.py prompt-lab/cases/001-auth-refresh

Prompt Lab deliberately does not call a model provider. The generated prompt
is meant for a fresh host session, and any response is saved manually beside
the case artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evidentloop.review.core.prompt import render_host_reviewer_prompt  # noqa: E402


def load_pack(case_dir: Path) -> dict:
    pack_path = case_dir / "pack.json"
    if not pack_path.exists():
        raise ValueError(f"{pack_path} not found")
    try:
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{pack_path} is not valid JSON: {exc}") from exc

    if not isinstance(pack, dict):
        raise ValueError(f"{pack_path} must contain a top-level JSON object")
    if pack.get("artifact_type") != "code_diff":
        raise ValueError(f"artifact_type must be 'code_diff', got '{pack.get('artifact_type')}'")
    if not isinstance(pack.get("diff"), str) or not pack["diff"].strip():
        raise ValueError("pack.json 'diff' is empty")
    if not isinstance(pack.get("changed_files"), list) or not pack["changed_files"]:
        raise ValueError("pack.json 'changed_files' is empty")

    return pack


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render the canonical EvidentLoop reviewer prompt for a saved case.",
        allow_abbrev=False,
    )
    parser.add_argument("case_dir", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    case_dir = args.case_dir
    if not case_dir.is_dir():
        print(f"Error: {case_dir} is not a directory", file=sys.stderr)
        return 1

    try:
        pack = load_pack(case_dir)
        prompt, _ = render_host_reviewer_prompt(pack)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    rendered_path = case_dir / "rendered-prompt.md"
    rendered_path.write_text(prompt, encoding="utf-8")
    print(f"Case: {case_dir.name}")
    print(f"Diff size: {len(pack['diff'])} chars")
    print(f"Intent: {pack.get('intent') or '(none)'}")
    print(f"Rendered prompt saved: {rendered_path}")
    print(
        "Paste this into a fresh host LLM session, then save the response "
        "beside the case artifacts."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
