"""Strict parsing and normalization for exported finding feedback."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from typing import Any, Iterable, Mapping


_ACTIONS = {"accept", "false_positive", "comment", "severity_override"}
_SEVERITIES = {"high", "medium", "low", "note"}
_COMMON_FIELDS = {
    "target_type",
    "target_id",
    "action",
    "fingerprint",
    "graph_id",
    "run_id",
    "created_at",
    "source_audit_sha256",
}
_SHA256_PREFIXED_LENGTH = 71
MAX_COMMENT_LENGTH = 4_000


class FeedbackError(ValueError):
    """Stable feedback rejection returned by the revision API."""

    def __init__(self, code: str, message: str, line: int | None = None) -> None:
        self.code = code
        self.message = message
        self.line = line
        super().__init__(message)

    def __str__(self) -> str:
        location = f" at line {self.line}" if self.line is not None else ""
        return f"{self.code}{location}: {self.message}"


def _valid_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _SHA256_PREFIXED_LENGTH
        and value.startswith("sha256:")
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _parse_timestamp(value: Any, line: int) -> str:
    if not isinstance(value, str):
        raise FeedbackError(
            "feedback.invalid_timestamp", "created_at must be a string", line
        )
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FeedbackError(
            "feedback.invalid_timestamp", "created_at must be ISO 8601", line
        ) from exc
    if parsed.tzinfo is None:
        raise FeedbackError(
            "feedback.invalid_timestamp",
            "created_at must include a timezone",
            line,
        )
    return value


def _parse_event(value: Any, line: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FeedbackError(
            "feedback.invalid_event", "each line must be a JSON object", line
        )
    action = value.get("action")
    if not isinstance(action, str) or action not in _ACTIONS:
        raise FeedbackError(
            "feedback.invalid_action", f"unsupported action: {action!r}", line
        )
    action_fields = (
        {"comment"}
        if action == "comment"
        else {"severity"}
        if action == "severity_override"
        else set()
    )
    allowed = _COMMON_FIELDS | action_fields
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise FeedbackError(
            "feedback.unknown_field",
            f"unknown fields: {', '.join(unknown)}",
            line,
        )
    required = _COMMON_FIELDS - {"source_audit_sha256"}
    required |= action_fields
    missing = sorted(required - set(value))
    if missing:
        raise FeedbackError(
            "feedback.missing_field",
            f"missing fields: {', '.join(missing)}",
            line,
        )
    for field in ("target_id", "graph_id", "run_id"):
        if (
            not isinstance(value[field], str)
            or not value[field]
            or any(character.isspace() for character in value[field])
        ):
            raise FeedbackError(
                "feedback.invalid_identity",
                f"{field} must be a non-empty identifier",
                line,
            )
    if value["target_type"] != "finding":
        raise FeedbackError(
            "feedback.invalid_target_type", "target_type must be finding", line
        )
    if not _valid_sha256(value["fingerprint"]):
        raise FeedbackError(
            "feedback.invalid_fingerprint",
            "fingerprint must be sha256:<64 lowercase hex>",
            line,
        )
    source_hash = value.get("source_audit_sha256")
    if source_hash is not None and not _valid_sha256(source_hash):
        raise FeedbackError(
            "feedback.invalid_source_hash",
            "source_audit_sha256 must be sha256:<64 lowercase hex>",
            line,
        )
    created_at = _parse_timestamp(value["created_at"], line)

    event = {field: value[field] for field in _COMMON_FIELDS if field in value}
    event["created_at"] = created_at
    if action == "comment":
        comment = value.get("comment")
        if comment is not None and not isinstance(comment, str):
            raise FeedbackError(
                "feedback.invalid_comment", "comment must be a string or null", line
            )
        if isinstance(comment, str) and not comment.strip():
            raise FeedbackError(
                "feedback.invalid_comment",
                "comment must contain non-whitespace text or be null",
                line,
            )
        if isinstance(comment, str) and len(comment) > MAX_COMMENT_LENGTH:
            raise FeedbackError(
                "feedback.comment_too_long",
                f"comment exceeds {MAX_COMMENT_LENGTH} characters",
                line,
            )
        event["comment"] = comment
    elif action == "severity_override":
        severity = value.get("severity")
        if severity is not None and (
            not isinstance(severity, str) or severity not in _SEVERITIES
        ):
            raise FeedbackError(
                "feedback.invalid_severity", f"unsupported severity: {severity!r}", line
            )
        event["severity"] = severity
    return event


def parse_feedback_jsonl(raw: bytes) -> list[dict[str, Any]]:
    """Parse UTF-8 JSONL and reject the complete input on any malformed line."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FeedbackError("feedback.invalid_utf8", "feedback must be UTF-8") from exc
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise FeedbackError("feedback.invalid_json", str(exc), line_number) from exc
        events.append(_parse_event(value, line_number))
    if not events:
        raise FeedbackError("feedback.empty", "feedback contains no events")
    return events


def normalize_feedback(
    events: Iterable[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    """Remove exact duplicates, reject competing values, and return a stable hash."""
    unique: dict[str, dict[str, Any]] = {}
    for event in events:
        normalized = dict(event)
        encoded = json.dumps(
            normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        unique.setdefault(encoded, normalized)

    slots: dict[tuple[str, str], str] = {}
    for encoded, event in unique.items():
        action = str(event["action"])
        slot = "disposition" if action in {"accept", "false_positive"} else action
        key = (str(event["target_id"]), slot)
        previous = slots.get(key)
        if previous is not None and previous != encoded:
            raise FeedbackError(
                "feedback.conflict",
                f"multiple {slot} events for finding {event['target_id']}",
            )
        slots[key] = encoded

    order = {"accept": 0, "false_positive": 0, "comment": 1, "severity_override": 2}
    normalized_events = sorted(
        unique.values(),
        key=lambda event: (str(event["target_id"]), order[str(event["action"])]),
    )
    canonical = json.dumps(
        normalized_events,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return normalized_events, f"sha256:{hashlib.sha256(canonical).hexdigest()}"
