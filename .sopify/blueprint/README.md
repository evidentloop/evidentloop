# change-audit Blueprint

## 状态

产品边界和一期方案已经确认，Wave 0A/0B/1/2/3/4 与最终验证 7.1–7.3 已完成。CrossReview 审查核心、code-diff schema `0.2`、renderer、`prepare/finalize`、changed-line 可信锚点、正式产物对、用户决策导出和自包含 AI host Skill 已落地；固定 Fireworks range 的真实报告已完成同源基线对比、样张专用架构图与 localhost DOM 验证。Qoder 模型级 smoke 由用户明确延后。

## 当前目标

交付一个产品、一个 Python 包和一个 AI host Skill：`change_audit.review` 是 artifact-general 隔离审查内核，正式 audit 能力按 artifact profile 成熟度放行；Python 负责可信上下文、结构化审计、校验和确定性呈现。

## 当前焦点

一期实现、README、封面、真实样张和工作树总审计已经收口，功能提交已 push 至开发分支。当前等待用户审阅；方案归档、tag、PyPI 发布和 CrossReview 旧仓库处理均不自动执行。

## 维护方式

本目录只保留长期真相：`background.md` 说明产品问题，`design.md` 说明稳定架构，`tasks.md` 只列未完成长期项。实现任务、验收门禁和已确认决策以当前方案包为准。

## 阅读入口

- [项目技术约定](../project.md)
- [产品背景](./background.md)
- [长期设计](./design.md)
- [长期任务](./tasks.md)
- [当前方案](../plan/20260710_audit_json_v0_schema_renderer_spike/plan.md)
- [变更历史](../history/index.md)
