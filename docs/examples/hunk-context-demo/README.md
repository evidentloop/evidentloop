# Hunk context 历史样张

本目录保存身份迁移前生成的 schema `0.2` renderer 样张，展示 finding 如何回链到可信 Git hunk。`audit.json` 与 `audit.html` 保留原始 provenance 和文件字节，只作为历史证据，不作为 EvidentLoop schema `0.3` fixture。

## 场景

- 目标：审计 auth token refresh 修复是否完整。
- 输入：`HEAD~1` 的本地 Git diff。
- 正式产物：包含 hunk context 的 `audit.json` 和对应 `audit.html`。
- 可选产物：用户在 HTML 中导出的 `audit-feedback.jsonl`。

## 样张展示的约束

- **可信 hunk**：prepare 解析 Git diff 并建立 hunk index；finalize 根据候选位置反查 `hunk_id` 并复制完整 hunk。Renderer 不读取 Git。
- **机械字段**：Python 生成 ID、edge、fingerprint、可信行范围和 highlight；host reviewer 只返回语义 finding 候选。
- **Finding card**：每条 finding 展示标题、位置、可信 diff 表格和关联 evidence；只有图中存在独立 fix 节点时才展示修复建议。
- **Diff 阅读**：新增、删除、上下文和命中行使用不同样式，并保留 old/new 双行号。
- **本地反馈**：按 graph、run 与 fingerprint 隔离 localStorage，支持接受、误报、评论和严重度调整，并导出合法 `audit-feedback.jsonl`。
- **双向回链**：finding、fingerprint、claim、anchored hunk 与 feedback target 都通过完整性校验。

## 冻结边界

当前 `python -m evidentloop render` 只接受 schema `0.3`，不用于覆盖本目录的 schema `0.2` HTML。新的样张应从新的 `prepare` 运行生成，不能改写本目录后继续沿用原 hash 或 provenance。
