"""Command-line interface for EvidentLoop."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .audit.finalize import AuditWorkflowError, finalize_review, prepare_local_diff
from .audit.fix_verification import (
    fix_verification_request_from_dict,
    prepare_fix_verification,
)
from .audit.revision import RevisionError, revise_audit
from .demo import DemoError, run_demo
from .doctor import collect_diagnostics, render_diagnostics
from .renderers.html import AuditRenderError, render_audit_file


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="evidentloop")
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="check the local EvidentLoop runtime")
    doctor.add_argument("--json", action="store_true", dest="as_json")
    demo = commands.add_parser("demo", help="run the bundled synthetic replay demo")
    demo.add_argument("--out", type=Path)
    prepare = commands.add_parser(
        "prepare", help="prepare a local Git diff for host review"
    )
    prepare.add_argument("--diff", dest="diff_spec", required=True)
    prepare.add_argument("--out", type=Path)
    prepare.add_argument("--focus", type=str, default=None)
    prepare.add_argument("--fix-verification", dest="fix_verification", type=Path)
    finalize = commands.add_parser("finalize", help="finalize a prepared host review")
    finalize.add_argument("--out", type=Path, required=True)
    finalize.add_argument("--keep-review-artifacts", action="store_true")
    render = commands.add_parser("render", help="render a validated audit.json")
    render.add_argument("input_json", type=Path)
    render.add_argument("--out", type=Path, required=True)
    revise = commands.add_parser(
        "revise", help="apply finding feedback to an audit report"
    )
    revise.add_argument("source_audit_json", type=Path)
    revise.add_argument("--feedback", type=Path, required=True)
    revise.add_argument("--out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "doctor":
        diagnostics = collect_diagnostics()
        if args.as_json:
            print(json.dumps(diagnostics, ensure_ascii=False, sort_keys=True))
        else:
            print(render_diagnostics(diagnostics))
        return 1 if diagnostics["status"] == "error" else 0
    if args.command == "demo":
        try:
            result = run_demo(args.out)
        except (DemoError, AuditWorkflowError) as exc:
            print(f"evidentloop demo: {exc}", file=sys.stderr)
            return 1
        print(
            "EvidentLoop demo: bundled synthetic fixture + frozen reviewer replay; "
            "no live AI review was performed.",
            file=sys.stderr,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "prepare":
        try:
            if args.fix_verification is not None:
                try:
                    request_document = json.loads(
                        args.fix_verification.read_text(encoding="utf-8")
                    )
                except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                    raise AuditWorkflowError(
                        f"cannot read fix verification request: {exc}"
                    ) from exc
                request = fix_verification_request_from_dict(request_document)
                result = prepare_fix_verification(
                    Path.cwd(), args.diff_spec, request, args.out, focus=args.focus
                )
            else:
                result = prepare_local_diff(
                    Path.cwd(), args.diff_spec, args.out, focus=args.focus
                )
        except AuditWorkflowError as exc:
            print(f"evidentloop prepare: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "finalize":
        try:
            result = finalize_review(args.out, args.keep_review_artifacts)
        except AuditWorkflowError as exc:
            print(f"evidentloop finalize: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "render":
        try:
            result = render_audit_file(args.input_json, args.out)
        except AuditRenderError as exc:
            print(f"evidentloop render: {exc}", file=sys.stderr)
            return 1
        print(result)
        return 0
    if args.command == "revise":
        try:
            result = revise_audit(args.source_audit_json, args.feedback, args.out)
        except RevisionError as exc:
            print(json.dumps(exc.to_dict(), ensure_ascii=False, sort_keys=True))
            return 1
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    return 2
