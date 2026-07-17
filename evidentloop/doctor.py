"""Deterministic runtime diagnostics for EvidentLoop installations."""

from __future__ import annotations

import shutil
import subprocess
import sys
from importlib.resources import files
from typing import Any

from . import __version__
from .review.core.prompt import (
    PRODUCT_REVIEWER_PROMPT_VERSION,
    get_default_reviewer_template,
)
from .validation import SCHEMA_VERSION, load_audit_schema


def _check(name: str, status: str, detail: str, *, blocking: bool) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "blocking": blocking,
        "detail": detail,
    }


def collect_diagnostics() -> dict[str, Any]:
    """Check only public runtime dependencies and bundled package resources."""
    checks: list[dict[str, Any]] = []
    version_status = "warning" if __version__.endswith(".dev0") else "ok"
    checks.append(
        _check(
            "version",
            version_status,
            f"EvidentLoop {__version__}",
            blocking=False,
        )
    )

    try:
        schema = load_audit_schema()
        schema_version = schema["properties"]["schema_version"]["const"]
        schema_id = schema["$id"]
        valid_schema = schema_version == SCHEMA_VERSION and schema_id.endswith(
            f"/schemas/audit-v{SCHEMA_VERSION}.schema.json"
        )
        checks.append(
            _check(
                "schema",
                "ok" if valid_schema else "error",
                f"schema {schema_version} · {schema_id}",
                blocking=True,
            )
        )
    except Exception as exc:
        checks.append(_check("schema", "error", str(exc), blocking=True))

    try:
        prompt = get_default_reviewer_template()
        valid_prompt = prompt.startswith(
            f"# EvidentLoop Reviewer Prompt Template (product/{PRODUCT_REVIEWER_PROMPT_VERSION})\n"
        )
        checks.append(
            _check(
                "prompt",
                "ok" if valid_prompt else "error",
                f"product/{PRODUCT_REVIEWER_PROMPT_VERSION}",
                blocking=True,
            )
        )
    except Exception as exc:
        checks.append(_check("prompt", "error", str(exc), blocking=True))

    try:
        resources = (
            ("evidentloop.renderers", "templates/audit.html.j2"),
            ("evidentloop.renderers", "static/audit.css"),
            ("evidentloop.renderers", "static/audit.js"),
            ("evidentloop.demo_resources", "fixture.json"),
        )
        for package, path in resources:
            if not files(package).joinpath(path).read_bytes():
                raise ValueError(f"empty package resource: {package}/{path}")
        checks.append(
            _check(
                "package_resources",
                "ok",
                f"{len(resources)} bundled resources readable",
                blocking=True,
            )
        )
    except Exception as exc:
        checks.append(_check("package_resources", "error", str(exc), blocking=True))

    git = shutil.which("git")
    if git:
        try:
            version = subprocess.run(
                [git, "--version"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            checks.append(_check("git", "ok", version, blocking=True))
        except (OSError, subprocess.SubprocessError) as exc:
            checks.append(_check("git", "error", str(exc), blocking=True))
    else:
        checks.append(_check("git", "error", "Git was not found on PATH", blocking=True))

    npx = shutil.which("npx")
    checks.append(
        _check(
            "npx",
            "ok" if npx else "warning",
            npx or "npx was not found; standard Skill installation is unavailable",
            blocking=False,
        )
    )

    blocking_failure = any(
        item["blocking"] and item["status"] == "error" for item in checks
    )
    has_warning = any(item["status"] == "warning" for item in checks)
    status = "error" if blocking_failure else ("warning" if has_warning else "ok")
    return {
        "status": status,
        "version": __version__,
        "python_executable": sys.executable,
        "checks": checks,
        "next_steps": {
            "skill_install": (
                "npx skills@latest add evidentloop/evidentloop "
                "--skill evidentloop -g"
            ),
            "manual_install": (
                "If the standard installer is unavailable, copy the complete "
                "skills/evidentloop directory from the release source using the "
                "AI host's documented global Skill installation method."
            ),
            "audit_request": (
                "Use EvidentLoop to audit my staged changes and generate the HTML report."
            ),
        },
    }


def render_diagnostics(diagnostics: dict[str, Any]) -> str:
    """Render diagnostics without leaking host-private paths beyond PATH results."""
    lines = [f"EvidentLoop doctor: {diagnostics['status']}"]
    markers = {"ok": "OK", "warning": "WARN", "error": "ERROR"}
    for item in diagnostics["checks"]:
        lines.append(
            f"[{markers[item['status']]}] {item['name']}: {item['detail']}"
        )
    steps = diagnostics["next_steps"]
    lines.extend(
        (
            f"Skill install: {steps['skill_install']}",
            f"Manual fallback: {steps['manual_install']}",
            f"Then ask: {steps['audit_request']}",
        )
    )
    return "\n".join(lines)
