# 本地仓库 dogfood 示例

本示例用 `audit-graph` 仓库自身的文档收口作为审计对象，定位是文档审计样张。

场景：

- 目标：审计 `audit-graph` 文档是否完成 HTML-first、SVG-optional、Markdown-export 的口径收口。
- 输入：本地文档变更、人工审计发现、摘要审计决策。
- 输出：`audit.json` 和 `audit.html`。

说明：

- 文档审计没有代码 hunk context，因此使用摘要、表格和证据关系展示。
- 文档审计样张不要求 finding 包含 `file_path`、`start_line`、`hunk`、`fingerprint` 等代码定位字段。
- 本示例不代表 v0 代码审计主形态。
- v0 代码审计主样张见 `../hunk-context-demo/`，它展示 finding card、hunk snippet 和用户反馈采集。

文件：

- `audit.json`：机器可读审计图谱示例。
- `audit.html`：默认人类审计视图示例。

该示例不是 renderer 产物，而是文档审计场景的产品形态样张，用于审计信息架构和数据模型是否合理。
