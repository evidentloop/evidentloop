# EvidentLoop Blueprint

## 状态

EvidentLoop v0 code-diff 一期与 Wave 5 单产品收口已经完成并归档。产品身份 checkpoint 与本地 clean break 已完成；当前 schema `0.3`、prompt `v0.4`、317 项测试、Skill、文档和视觉资产已统一为 EvidentLoop，历史报告保持原样。

## 当前目标

公开交付物收敛为 PyPI CLI、同仓库标准薄 Skill 和 GitHub Pages。用户可以先在线看报告、再用 `uvx` 运行 replay demo，正式使用时安装 CLI 与 Skill 后用一句自然语言生成 `audit.json + audit.html`。Schema `0.3` 当前只支持 Git diff；机械审计契约不因分发方式变化而弱化。

## 当前焦点

当前焦点是等待用户审计[产品身份与分发方案](../plan/20260711_identity_and_distribution/background.md) Wave 1 实现。确认前不进入 Wave 2；远端 repository 改名、域名、PyPI、tag、Pages 与发布仍需后续 checkpoint。

## 维护方式

本目录只保留长期真相：`background.md` 说明产品问题，`design.md` 说明稳定架构，`tasks.md` 只列未完成长期项。已完成任务、验收门禁和决策证据保存在归档方案中。

## 阅读入口

- [项目技术约定](../project.md)
- [产品背景](./background.md)
- [长期设计](./design.md)
- [长期任务](./tasks.md)
- [产品身份与分发方案](../plan/20260711_identity_and_distribution/background.md)
- [已归档的一期方案](../history/2026-07/20260710_audit_json_v0_schema_renderer_spike/plan.md)
- [变更历史](../history/index.md)
