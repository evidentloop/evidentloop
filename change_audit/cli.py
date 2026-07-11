"""Command-line interface for change-audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit.finalize import AuditWorkflowError, finalize_review, prepare_local_diff
from .renderers.html import AuditRenderError, render_audit_file


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m change_audit")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="prepare a local Git diff for host review")
    prepare.add_argument("--diff", dest="diff_spec", required=True)
    prepare.add_argument("--out", type=Path)
    finalize = commands.add_parser("finalize", help="finalize a prepared host review")
    finalize.add_argument("--out", type=Path, required=True)
    finalize.add_argument("--keep-review-artifacts", action="store_true")
    render = commands.add_parser("render", help="render a validated audit.json")
    render.add_argument("input_json", type=Path)
    render.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "prepare":
        try:
            result = prepare_local_diff(Path.cwd(), args.diff_spec, args.out)
        except AuditWorkflowError as exc:
            print(f"change-audit prepare: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "finalize":
        try:
            result = finalize_review(args.out, args.keep_review_artifacts)
        except AuditWorkflowError as exc:
            print(f"change-audit finalize: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "render":
        try:
            result = render_audit_file(args.input_json, args.out)
        except AuditRenderError as exc:
            print(f"change-audit render: {exc}", file=sys.stderr)
            return 1
        print(result)
        return 0
    return 2
