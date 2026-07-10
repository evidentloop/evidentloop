# change-audit Blueprint

## 状态

已完成项目初始化与 `change-audit` 正式改名。长期蓝图已创建，尚未开始实现代码。

## 维护方式

本文件只作为索引。产品背景写入 `background.md`，架构契约写入 `design.md`，延后任务写入 `tasks.md`。

## 当前目标

将 `change-audit` 定义为独立的 AI 代码变更审计工具，可消费 CrossReview 结果，后续也可集成到 Sopify；Audit Graph 只作为内部数据模型。

## 当前焦点

冻结 `audit.json` v0 schema，并通过 renderer-first spike 验证首张 finding card。

## 深入阅读

- [项目技术约定](../project.md)
- [蓝图背景](./background.md)
- [蓝图设计](./design.md)
- [长期任务](./tasks.md)
- [初始化方案归档](../history/2026-07/20260707_audit_graph_init/background.md)
- [正式改名方案归档](../history/2026-07/20260710_change_audit_rename/background.md)
- [变更历史](../history/index.md)
