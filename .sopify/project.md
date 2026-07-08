# audit-graph 项目约定

## 产品

`audit-graph` 是一个独立开源项目，用于生成可视化审计证据图谱。

核心定位：

```text
面向 AI 技术变更的可视化审计证据图谱。
```

中文是主要产品文档语言。英文只保留在项目名、包元数据、命令、字段名和通用技术术语中。

## 技术方向

- 语言：第一版计划使用 Python，与 `cross-review` 保持一致。
- 运行形态：独立 CLI 优先，可导入 core 其次。
- 渲染方式：默认生成本地 HTML，静态 SVG 作为可选概览图，v0 不引入前端构建链。
- 集成方式：通过 adapter 消费 CrossReview `ReviewResult`，不依赖 CrossReview 内部实现。
- 产品形态：独立优先、可嵌入工作流，工作流集成必须保持可选。
- 审计范围：同时覆盖变更理解和问题审查。
- 默认产物：`audit.json` 和 `audit.html`。
- 可选产物：`audit-graph.svg` 和 Markdown 导出。

## 命名

- 项目目录：`audit-graph`
- Python 包名候选：`auditgraph`
- CLI 名称候选：`audit-graph`

## 当前约束

本次初始化不添加实现代码。源码目录仅作为后续实现占位。
