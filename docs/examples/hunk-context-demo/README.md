# Hunk context demo

本示例是 Wave 1 renderer 的主样张，展示 `audit.html` 如何从同目录 `audit.json` 确定性生成，并在 finding 旁嵌入可信代码变更上下文（hunk snippet）。

场景：

- 目标：审计 auth token refresh 修复是否完整。
- 输入：`HEAD~1` 的本地 Git diff。
- 输出：`audit.json`（含 hunk context）和 `audit.html`（带代码上下文的审计视图）。
- 可选输出：用户在 HTML 中导出的 `audit-feedback.jsonl`。

核心设计点：

- **可信 hunk 嵌入**：prepare 解析 Git diff 并建立可信 hunk index；finalize 根据候选位置反查 `hunk_id` 并复制完整 hunk。renderer 不直接读 Git。
- **扁平 finding 字段**：finding 直接包含 `file_path`、`hunk_id`、`start_line`、`end_line`、`line_side`、`highlight_lines`、`hunk`、`fingerprint`。
- **语义与机械字段分离**：host LLM 生成语义 finding 候选；Python 生成 ID、edge、fingerprint 和可信定位字段。
- **finding card**：每个 finding 展示为一个卡片，包含标题、位置、可信 diff 表格和关联证据；只有图中存在独立 fix 节点时才展示修复建议。
- **代码装饰条**：hunk 左侧有橙色竖线标记 `highlight_lines` 指定的关键行。
- **diff 着色**：绿色底 = 新增行，红色底 = 删除行，无底色 = 上下文行。
- **人工决策闭环**：按 graph、run 与 fingerprint 隔离 localStorage；支持接受、误报、评论、严重度调整，并显式导出合法 `audit-feedback.jsonl`。浏览器下载位置不保证等于本目录。
- **审计回链**：finding/fingerprint、claim、anchored hunk 和 feedback target 都有双向完整性校验；可视关系保留对应 `data-*` 标识。

`audit.html` 现在是 renderer 的真实产物，不再是手工模板。重新生成命令：

```bash
python -m change_audit render docs/examples/hunk-context-demo/audit.json \
  --out docs/examples/hunk-context-demo/audit.html
```

生成过程先执行 schema、引用、锚点、状态与计数校验，再验证 HTML identity 和 `data-*` 回链；任一失败都保留旧 HTML 且不修改输入 JSON。
