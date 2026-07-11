"""Canonical reviewer prompt seam for product and eval usage."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from importlib.resources import files
from typing import Any

from change_audit.review.schema import to_serializable


PRODUCT_REVIEWER_PROMPT_SOURCE = "product"
PRODUCT_REVIEWER_PROMPT_VERSION = "v0.2"


DEFAULT_REVIEWER_TEMPLATE = files(__package__).joinpath("reviewer-prompt.md").read_text(
    encoding="utf-8"
)


def get_default_reviewer_template() -> str:
    """Return the built-in product prompt template."""
    return DEFAULT_REVIEWER_TEMPLATE


def _normalize_pack(pack: Any) -> dict[str, Any]:
    if is_dataclass(pack):
        return to_serializable(pack)
    if isinstance(pack, dict):
        return pack
    return asdict(pack)


def _render_changed_files(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "(no changed files provided)"
    rendered: list[str] = []
    for item in value:
        if isinstance(item, dict):
            path = item.get("path", "<unknown>")
            language = item.get("language")
            suffix = f" ({language})" if language else ""
            rendered.append(f"- {path}{suffix}")
        else:
            rendered.append(f"- {item}")
    return "\n".join(rendered)


def _render_context_files(value: Any) -> str:
    if not isinstance(value, list) or not value:
        return "(no context files provided)"
    chunks: list[str] = []
    for item in value:
        if not isinstance(item, dict):
            chunks.append(str(item))
            continue
        title = item.get("path", "<unknown>")
        role = item.get("role")
        role_suffix = f" [{role}]" if role else ""
        content = item.get("content", "")
        chunks.append(f"### {title}{role_suffix}\n```text\n{content}\n```")
    return "\n\n".join(chunks)


def render_reviewer_prompt(template: str, pack: Any) -> str:
    """Render the canonical reviewer prompt from a ReviewPack-like object."""
    normalized = _normalize_pack(pack)
    return template.format(
        intent=normalized.get("intent") or "(no intent provided)",
        task_file=normalized.get("task_file") or "(no task file provided)",
        focus=", ".join(normalized.get("focus") or []) or "(no focus specified)",
        context_files=_render_context_files(normalized.get("context_files")),
        changed_files=_render_changed_files(normalized.get("changed_files")),
        evidence=json.dumps(normalized.get("evidence") or [], indent=2, ensure_ascii=False),
        diff=normalized.get("diff", ""),
    )
