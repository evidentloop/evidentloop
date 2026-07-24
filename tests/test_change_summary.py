"""Focused tests for semantic change-summary parsing."""

from __future__ import annotations

import pytest

from evidentloop.review.change_summary import parse_change_summary


def _section(count: int) -> str:
    themes = "\n\n".join(
        (
            f"### theme-{index:03d}\n"
            f"- **Title**: 逻辑主题 {index}\n"
            f"- **Summary**: 说明第 {index} 项行为变化。\n"
            f"- **Impact**: 模块 {index}"
        )
        for index in range(1, count + 1)
    )
    return (
        "## Section 0: Change Summary\n\n"
        "- **Overview**: 本次改动形成可理解的业务变化。\n"
        "- **Review focus**: 重点核验关键链路是否保持一致。\n\n"
        f"{themes}\n\n"
        "## Section 1: Findings\n\nNo findings.\n"
    )


@pytest.mark.parametrize("count", [1, 3, 5])
def test_parser_accepts_model_selected_theme_count(count: int) -> None:
    result = parse_change_summary(_section(count))

    assert result is not None
    assert result["overview"] == "本次改动形成可理解的业务变化。"
    assert result["review_focus"] == "重点核验关键链路是否保持一致。"
    assert len(result["themes"]) == count
    assert result["themes"][-1]["impact"] == f"模块 {count}"


@pytest.mark.parametrize(
    "raw",
    [
        "## Section 1: Findings\n\nNo findings.\n",
        _section(1).replace(
            "- **Overview**: 本次改动形成可理解的业务变化。\n",
            "- **Overview**: 第一项。\n- **Overview**: 第二项。\n",
        ),
        _section(1).replace("### theme-001", "### fixed-module"),
        _section(1).replace("### theme-001", "### theme-002"),
        _section(2).replace("### theme-002", "### theme-003"),
        _section(6),
    ],
)
def test_parser_discards_malformed_summary(raw: str) -> None:
    assert parse_change_summary(raw) is None
