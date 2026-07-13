# EvidentLoop Blueprint

## 状态

EvidentLoop v0 code-diff 一期与 Wave 5 单产品收口已经完成并归档。产品身份 checkpoint、本地 clean break、Python CLI 产品化、Wave 3 Skill 安装/discovery 与 Wave 4 Codex 真实审计 E2E 已完成；当前 schema `0.3`、prompt `v0.4`、327 项测试、Skill、文档和视觉资产已统一为 EvidentLoop，历史报告保持原样。

## 当前目标

公开交付物收敛为 PyPI CLI、同仓库标准薄 Skill 和 GitHub Pages。用户可以先在线看报告、再用 `uvx` 运行 replay demo，正式使用时安装 CLI 与 Skill 后用一句自然语言生成 `audit.json + audit.html`。Schema `0.3` 当前只支持 Git diff；机械审计契约不因分发方式变化而弱化。

## 当前焦点

当前焦点是[产品身份与分发方案](../plan/20260711_identity_and_distribution/background.md)的 Wave 4；历史 clean 安装与 Codex CLI `0.144.1`、`0.144.3` 的隔离 reviewer E2E 仍有效，但 Wave 4.3 的固定产物外部复跑在 reviewer 前暴露了安装解释器和 Skill runtime discovery 阻塞。`74c7d16` 候选已退役；当前只修复显式 Python 安装、console doctor 引导解释器及禁止跨目录寻找安装来源，冻结新候选后再次复跑。4.3 未完成，4.4 未开始。

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
