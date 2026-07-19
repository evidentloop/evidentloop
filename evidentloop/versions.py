"""Deterministic versions for diff and report artifacts."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping


_CONTENT_VERSION_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def content_version(raw: bytes) -> str:
    """Return the version of exact artifact bytes."""
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def diff_version_from_fingerprint(fingerprint: str) -> str:
    """Expose the existing raw-diff fingerprint as a version value."""
    value = f"sha256:{fingerprint}"
    if not is_content_version(value):
        raise ValueError("diff fingerprint is not a SHA-256 hex digest")
    return value


def is_content_version(value: object) -> bool:
    return isinstance(value, str) and _CONTENT_VERSION_RE.fullmatch(value) is not None


def audit_diff_version(audit: Mapping[str, Any]) -> str | None:
    extensions = audit.get("extensions")
    if not isinstance(extensions, Mapping):
        return None
    evidentloop = extensions.get("evidentloop")
    if not isinstance(evidentloop, Mapping):
        return None
    value = evidentloop.get("diff_version")
    return value if isinstance(value, str) else None
