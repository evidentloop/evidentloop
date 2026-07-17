"""Synthetic audit fixtures for schema and renderer tests."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def demo_audit() -> dict[str, Any]:
    return json.loads(
        (ROOT / "tests/fixtures/audit-v0.4.json").read_text(encoding="utf-8")
    )


def fingerprint(label: str) -> str:
    return "sha256:" + hashlib.sha256(label.encode("utf-8")).hexdigest()


def minimal_audit(
    *,
    review_status: str = "complete",
    verdict: str = "pass_candidate",
    risk_score: int | None = 0,
) -> dict[str, Any]:
    run_id = "run-minimal"
    change_id = "change-minimal"
    file_id = "file-minimal"
    return {
        "schema_version": "0.4",
        "graph_id": f"audit:minimal:{review_status}",
        "source": {
            "type": "git_diff",
            "ref": "HEAD~1",
            "description": "minimal audit",
        },
        "runs": [
            {
                "id": run_id,
                "label": "Minimal audit",
                "status": verdict,
                "summary": "Synthetic renderer state fixture.",
                "kind": "model_review",
            }
        ],
        "nodes": [
            {
                "id": change_id,
                "type": "change",
                "title": "Synthetic change",
                "summary": "Small deterministic fixture.",
            },
            {
                "id": file_id,
                "type": "file",
                "path": "src/example.py",
                "role": "implementation",
                "change_type": "modified",
                "additions": 1,
                "deletions": 1,
            },
        ],
        "edges": [
            {
                "id": "edge-run-change",
                "type": "contains_change",
                "from": run_id,
                "to": change_id,
            },
            {
                "id": "edge-change-file",
                "type": "changes_file",
                "from": change_id,
                "to": file_id,
            },
        ],
        "summary": {
            "review_status": review_status,
            "verdict": verdict,
            "risk_score": risk_score,
            "finding_count": 0,
            "unscored_finding_count": 0,
            "open_finding_count": 0,
            "fix_count": 0,
            "fix_done_count": 0,
            "summary_audit_status": "not_audited",
            "basis": "model_review",
        },
    }


def unanchored_risk_audit(*, review_status: str = "complete") -> dict[str, Any]:
    verdict = "needs_human_triage" if review_status == "complete" else "inconclusive"
    audit = minimal_audit(
        review_status=review_status,
        verdict=verdict,
        risk_score=None,
    )
    finding = {
        "id": "finding-unanchored",
        "type": "finding",
        "category": "risk",
        "severity": "medium",
        "status": "open",
        "title": "Semantic concern without exact location",
        "detail": "The review found a real concern but could not resolve a trusted hunk.",
        "fingerprint": fingerprint("finding-unanchored"),
        "model_judgment": {"status": "open", "severity": "medium"},
        "extensions": {
            "evidentloop": {
                "original_category": "logic_error",
                "downgraded_from": "bug",
                "downgrade_reason": "line_outside_trusted_hunk",
            }
        },
    }
    audit["nodes"].append(finding)
    audit["summary"].update(
        {
            "finding_count": 1,
            "unscored_finding_count": 1,
            "open_finding_count": 1,
        }
    )
    return audit


def cloned(value: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(value)
