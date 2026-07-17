---
plan_id: 20260716_feedback_revision_loop
outcome: completed
---

# completed

## Summary

EvidentLoop schema `0.4` 反馈裁定闭环已完成：用户在报告中记录裁定后，可以把机器块交给 AI 更新同一路径报告；模型原判断、人工裁定和当前结论分别保留。Runtime 不重新审查代码，也不修改业务代码。

## Verification

- Python 全量测试 `368 passed`；CLI/Skill 定向回归 `43 passed`。
- Ruff、Node、Skill 校验、`git diff --check` 和 clean build 通过。
- Clean wheel 为 package `0.1.0a1` / schema `0.4`，不包含 schema `0.3` resource；doctor、module CLI、demo、同路径 revision 与 release boundary smoke 通过。
- 提交前正式 staged 审计发现整目录切换等 3 项边界；按确认收敛为只管理 `audit.json + audit.html`、精确拒绝内部恢复路径，并在副本校验失败时退回隐藏 staging。

## Key Decisions

- 默认更新原报告；只有用户明确要求时才另存副本。
- 人工裁定可以形成候选通过，但必须说明“基于人工裁定，未重新审查代码”。
- 过期、冲突、来源不唯一或恢复状态不确定时停止，不自动猜测或合并。
- 当前 runtime clean break 到 schema `0.4`；已发布 schema `0.3` 报告只读保留。
- Alpha 已知边界：若用户预先创建与内部 candidate/backup 完全同名的隐藏目录，恢复清理可能删除该目录；本期不增加所有权标记，后续根据真实反馈评估。

## Publication

本次 finalize 先完成本地归档；归档随后按用户确认纳入本功能提交。尚未推送，也未创建 PR、tag、GitHub Release 或 PyPI 发布。
