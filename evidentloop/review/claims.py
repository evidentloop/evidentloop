"""Parser for the reviewer's single Fix Verification Results block.

The block is part of the v0.7 reviewer contract: when fix-verification
claims are supplied, the reviewer must output exactly one entry per input
``claim_id`` under ``## Section 4: Fix Verification Results``. Strictness
here feeds the completion gate — any missing, duplicated, unknown, or
malformed entry downgrades the run instead of being silently dropped.
"""

from __future__ import annotations

import re
from typing import Sequence


CLAIM_STATUSES = ("supported", "challenged", "partial", "unknown")

_SECTION_RE = re.compile(
    r"(?ms)^#+\s*Section 4:\s*Fix Verification Results\s*(.*?)(?=^#+\s*Section\s+\d+:|\Z)"
)
_ENTRY_RE = re.compile(r"(?ms)^###\s+(claim-\d+)\s*(.*?)(?=^###\s+claim-\d+|\Z)")
_ENTRY_HEADING_RE = re.compile(r"(?m)^###\s+(.+?)\s*$")
_FIELD_RE_TEMPLATE = r"(?m)^-\s*\*\*{label}\*\*:\s*(.+?)\s*$"


def _field(block: str, label: str) -> str | None:
    matches = re.findall(_FIELD_RE_TEMPLATE.format(label=label), block)
    if len(matches) != 1:
        return None
    value = matches[0].strip()
    return value or None


def parse_fix_verification_results(
    raw_analysis: str,
    expected_claim_ids: Sequence[str],
) -> tuple[list[dict[str, str]], list[str]]:
    """Parse Section 4 and return (ordered results, problems).

    Results preserve the expected target order. Any deviation from the
    one-entry-per-claim contract is reported in problems, and the caller
    treats a non-empty problem list as an incomplete run.
    """
    expected = list(expected_claim_ids)
    sections = list(_SECTION_RE.finditer(raw_analysis))
    if not sections:
        return [], [
            f"missing Fix Verification Results block for {len(expected)} claim(s)"
        ]
    if len(sections) != 1:
        return [], [
            f"expected exactly one Fix Verification Results block, found {len(sections)}"
        ]

    parsed: dict[str, dict[str, str]] = {}
    problems: list[str] = []
    section_body = sections[0].group(1)
    for heading in _ENTRY_HEADING_RE.findall(section_body):
        if heading not in expected and not re.fullmatch(r"claim-\d+", heading):
            problems.append(f"unknown claim_id in results: {heading}")
    for claim_id, block in _ENTRY_RE.findall(section_body):
        if claim_id not in expected:
            problems.append(f"unknown claim_id in results: {claim_id}")
            continue
        if claim_id in parsed:
            problems.append(f"duplicate claim_id in results: {claim_id}")
            continue
        status = _field(block, "Status")
        reason = _field(block, "Reason")
        evidence = _field(block, "Evidence")
        if status not in CLAIM_STATUSES:
            problems.append(f"{claim_id} has invalid status: {status!r}")
            continue
        if reason is None:
            problems.append(f"{claim_id} is missing a non-empty Reason")
        if evidence is None:
            problems.append(f"{claim_id} is missing a non-empty Evidence")
        elif status == "unknown" and evidence.lower() != "none":
            problems.append(f"{claim_id} with unknown status must use Evidence: none")
        elif status != "unknown" and evidence.lower() == "none":
            problems.append(
                f"{claim_id} with {status} status requires concrete Evidence"
            )
        if (
            reason is None
            or evidence is None
            or any(problem.startswith(f"{claim_id} with ") for problem in problems)
        ):
            continue
        parsed[claim_id] = {
            "claim_id": claim_id,
            "status": status,
            "reason": reason,
            "evidence": evidence,
        }

    for claim_id in expected:
        if claim_id not in parsed and not any(
            problem.startswith(f"duplicate claim_id in results: {claim_id}")
            or problem.startswith(f"{claim_id} ")
            for problem in problems
        ):
            problems.append(f"missing result for claim_id: {claim_id}")

    results = [parsed[claim_id] for claim_id in expected if claim_id in parsed]
    return results, problems


def aggregate_claim_status(statuses: Sequence[str]) -> str:
    """Collapse per-claim statuses into the run-level summary_audit status."""
    if not statuses:
        return "not_audited"
    unique = set(statuses)
    if len(unique) == 1:
        return next(iter(unique))
    return "partial"
