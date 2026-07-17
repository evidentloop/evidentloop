# EvidentLoop Blueprint

## 状态

EvidentLoop v0 code-diff 一期与最小反馈裁定闭环已完成并归档。`v0.1.0a0` 首个公开 Alpha 的交付证据保持不变；当前未提交候选为 package `0.1.0a1`、schema `0.4`、prompt `v0.5`，历史报告保持只读。

## 当前目标

公开交付物收敛为 PyPI CLI、同仓库标准薄 Skill 和 GitHub Pages。正式使用时安装 CLI 与 Skill，用自然语言生成 `audit.json + audit.html`，再从报告复制人工裁定给 AI 更新同一路径。Schema `0.4` 当前仍只支持 Git diff。

## 当前焦点

最小反馈消费与报告 revision 已通过实现、自审和独立复审并完成 finalize。当前焦点回到[长期任务](./tasks.md)；提交、PR 与发布仍需分别确认，不扩张 code-diff 边界。

## 维护方式

本目录只保留长期真相：`background.md` 说明产品问题，`design.md` 说明稳定架构，`tasks.md` 只列未完成长期项。已完成任务、验收门禁和决策证据保存在归档方案中。

## 阅读入口

- [项目技术约定](../project.md)
- [产品背景](./background.md)
- [长期设计](./design.md)
- [长期任务](./tasks.md)
- [已归档的产品身份与分发方案](../history/2026-07/20260711_identity_and_distribution/background.md)
- [已归档的一期方案](../history/2026-07/20260710_audit_json_v0_schema_renderer_spike/plan.md)
- [已归档的反馈裁定闭环方案](../history/2026-07/20260716_feedback_revision_loop/background.md)
- [变更历史](../history/index.md)
