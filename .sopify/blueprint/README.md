# EvidentLoop Blueprint

## 状态

EvidentLoop v0 code-diff 一期已经完成并归档。产品身份、本地 clean break、Python CLI、标准 Skill 和 Codex 端到端审计已完成；当前 schema `0.3`、prompt `v0.5`，历史报告保持原样。

## 当前目标

公开交付物收敛为 PyPI CLI、同仓库标准薄 Skill 和 GitHub Pages。在线样例与 `uvx` replay demo 是可选体验入口；正式使用时安装 CLI 与 Skill，用一句自然语言生成 `audit.json + audit.html`。Schema `0.3` 当前只支持 Git diff。

## 当前焦点

当前焦点是[产品身份与分发方案](../plan/20260711_identity_and_distribution/background.md)。Wave 4 已完成并合入 main，`e6f3381` 保留为固定验证候选。repository 已改名为 `evidentloop/evidentloop`；Wave 5 的安装产物边界已完成，正在收口 Pages dogfood 与 GitHub Release evidence，`.sopify` 继续保留在 main。

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
