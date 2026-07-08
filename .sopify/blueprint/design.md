# audit-graph 设计

## 架构

计划模块：

- `auditgraph.schema`：图谱类型和序列化契约。
- `auditgraph.runs`：审计运行和快照建模。
- `auditgraph.adapters.gitdiff`：将 Git diff 元数据、变更文件和 finding hunk context 转换成图谱节点。
- `auditgraph.adapters.crossreview`：导入 CrossReview `ReviewResult`。
- `auditgraph.adapters.evidence`：导入确定性证据摘要。
- `auditgraph.graph`：归一化并连接节点和边。
- `auditgraph.renderers.html`：渲染默认审计视图 `audit.html`，包含 hunk snippet 和反馈采集。
- `auditgraph.renderers.svg`：可选渲染概览图 `audit-graph.svg`。
- `auditgraph.renderers.markdown`：可选导出摘要或修复清单。
- `auditgraph.cli`：暴露 build 和 render 命令。

## 数据流

```text
Git diff / CrossReview / evidence
  -> adapters
  -> audit run
  -> audit graph
  -> audit.json
  -> audit.html
  -> optional: audit-feedback.jsonl / audit-graph.svg / Markdown export
```

`audit-feedback.jsonl` 由 `audit.html` 的静态交互导出，不在 v0 build 阶段消费。

## 集成契约

CrossReview 作为输入格式被消费。`audit-graph` 在 v0 不应导入 CrossReview 的私有内部实现。

当配置审计 checkpoint 时，Sopify 可以在 develop 完成后、finalize 前调用 `audit-graph`。该集成是可选能力；独立 CLI 使用仍是主产品路径。

tech-report 生成叙事型技术报告时，可以读取 `audit.json` 或生成产物。

## 渲染规则

渲染器只消费归一化后的图谱数据，不能回头解析 Git、CrossReview 或原始证据文件。

本地编辑器跳转链接不写入 `audit.json`。HTML renderer 可以根据 repo root 和用户编辑器偏好生成 `vscode://` 等链接；链接不可用时，页面仍必须依靠 hunk snippet 独立可读。

## finding 代码上下文

v0 的 finding 使用扁平字段：

```json
{
  "file_path": "src/auth_service.py",
  "start_line": 38,
  "end_line": 52,
  "line_side": "new",
  "highlight_lines": [39, 40, 41],
  "hunk": "@@ -38,10 +38,14 @@\n...",
  "fingerprint": "sha256:..."
}
```

`hunk` 是 build 阶段提取的 render-ready unified diff snippet。Renderer 可以按行读取该字符串生成高亮代码块，但不得从 Git 重新读取。

`highlight_lines` 是装饰条依据。Renderer 不应从 finding 描述或 hunk 文本中猜测关键行。

## HTML 信息架构

`audit.html` 是默认人类审计视图。页面按用户问题组织，而不是按内部节点类型堆字段。

页面顺序：

- 审计结论：本轮状态、风险评分、finding 数量、失败证据数量、建议动作。
- 变更摘要：任务意图、变更范围、影响文件、行为变化、继续优化点，以及摘要审计状态。
- 问题清单：按 severity 和可操作性排序，以 finding card 展示位置、hunk snippet、原因、证据、修复入口和用户决策控件。
- 修复方案：按优先级展示建议动作、涉及文件、验证方式和状态。
- 多轮对比：展示新增、已修复、仍存在问题和风险评分变化；单 run 时降级成短提示。
- 证据详情：展示 CrossReview、test、lint、typecheck、安全扫描等证据来源。
- 可选概览图：仅当实际生成 `audit-graph.svg` 或存在 SVG artifact 时渲染。

v0 交互保持轻量：折叠详情、按 severity 过滤、按文件筛选、finding 决策采集、localStorage 暂存和 JSONL 导出。不引入复杂前端构建链。

## 用户反馈

v0 做反馈采集端，不做反馈消费端。

`audit.html` 支持用户对 finding 执行：

- `false_positive`
- `accept`
- `comment`
- `severity_override`

导出文件为 `audit-feedback.jsonl`：

```json
{"target_type":"finding","target_id":"finding-001","action":"accept","reason":"确认缓存路径仍有风险","fingerprint":"sha256:...","created_at":"2026-07-08T10:30:00+08:00"}
```

后续版本可以通过 `build --feedback audit-feedback.jsonl` 将反馈转换为 `user_decision` 节点或其他审计关系。

## 摘要审计规则

用户需要审计变更摘要是否准确，但 `summary` 不作为图谱节点类型。

建模方式：

- `run` 或 `change` 持有 `summary`、`summary_audit` 和 claims 字段。
- finding 或 evidence 通过 `supports_claim` / `challenges_claim` 边支持或挑战某条摘要声明。
- `audit.html` 展示完整摘要审计，包括“成立、部分成立、被挑战、未知”状态。
- `audit-graph.svg` 只在 change 节点上展示摘要审计 badge，不展开完整摘要内容。

这能保留摘要审计能力，同时避免把 `summary`、`overview`、`section` 等 UI 展示块引入核心数据模型。

## SVG 规则

v0 只支持一种可选 SVG 图：Audit Graph，输出文件名为 `audit-graph.svg`。

渲染器可以复用 SVG diagram skill 的工程方法：确定性模板、XML 转义、marker 校验和可选 PNG 导出。但不继承泛化图种、多套视觉风格或重图标渲染路线。

SVG 只做概览，不承载完整审计详情。完整的变更摘要、问题清单、修复方案、多轮对比和用户决策采集由 `audit.html` 承担。

核心布局：

```text
change/task -> files -> findings -> evidence/fixes
```

节点较多时，SVG 只展示 top risks 和汇总节点；完整列表由 `audit.html` 承担。

## SVG 生成策略

SVG 必须从 `audit.json` 或内存中的归一化图谱对象生成，不从自然语言、Markdown 或聊天上下文直接生成。

推荐管线：

```text
audit.json
  -> graph normalize
  -> Audit Graph template
  -> audit-graph.svg
  -> XML validation
  -> audit trace validation
```

实现约束：

- 布局采用确定性列布局，第一版不引入复杂自动布局。
- 文本统一 XML 转义。
- SVG 元素保留 `data-node-id` 或 `data-edge-id`，确保能回到 `audit.json`。
- 风险颜色只由 severity、evidence status 和 fix status 决定。
- 每个 finding 节点必须回链到原始 finding 或规则来源。
- 每条 evidence 边必须引用真实 evidence id。
- 不做多图种、多 style、图标库和自然语言任意画图。

质量判断：

```text
SVG valid = XML valid + audit trace valid
```
