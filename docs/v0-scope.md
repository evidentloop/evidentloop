# audit-graph v0 范围

## 核心假设

AI coding 让单次任务的改动规模和迭代速度变大。用户需要的不只是事后报告，而是可以独立运行、也可以嵌入工作流的审计证据层。

`audit-graph` 的第一版聚焦把代码变更、审查结论、确定性证据和用户审计决策转成结构化产物。HTML 是默认人类审计界面，必须展示 finding 相关代码上下文，而不是只给表格摘要。SVG 是可选概览图。

定位原则：

- standalone-first：可以单独对本地 Git diff 生成审计产物。
- workflow-ready：可以嵌入 Sopify 等 AI coding 工作流，作为 develop 后的审计 checkpoint。
- HTML-first：`audit.html` 是默认人类审计视图。
- hunk-context-first：默认展示 finding 相关 hunk snippet，不默认展开完整 diff viewer。
- feedback-capture：v0 支持在 HTML 中采集用户决策并导出 JSONL，但不消费反馈影响下一轮审计。
- SVG-optional：`audit-graph.svg` 是可选概览图，只表达风险分布和关键链路。
- Markdown-export：Markdown 只作为 PR、Issue 或聊天窗口的轻量导出，不作为默认产物。

## 审计层次

V0 按三类问题组织输出：

1. 变更理解

回答这次任务改了什么、影响哪里、实现路径是否符合意图、还有哪些优化点。默认在 `audit.html` 中展示；需要命令行或 PR 文本时，可导出 Markdown 摘要。

变更摘要本身也需要被审计。AI 可能漏掉关键文件、夸大修复范围，或把“部分修复”写成“已完全修复”。V0 将摘要作为 `change` 或 `run` 的字段审计，而不是新增 `summary` 节点类型。

摘要审计需要回答：

- 摘要是否覆盖关键变更。
- 摘要是否与 diff、finding 和 evidence 一致。
- 摘要是否需要降级为“部分成立”或“需要修正”。

2. 问题审查

回答有没有 bug、风险、遗漏边界、失败证据，以及修复是否收敛。`audit.html` 必须在每个 finding 旁展示代码 hunk snippet、关联 evidence 和建议 fix。`audit-graph.svg` 只展示概览。

3. 用户审计决策

回答用户是否认可 finding、是否认为它是误报、是否需要调整 severity 或补充上下文。V0 只做采集端：静态 HTML 使用 JavaScript 和 localStorage 临时保存用户操作，并支持导出 `audit-feedback.jsonl`。

反馈消费、`build --feedback`、`user_decision` 节点和 `suppressed_by` 这类边进入后续版本。

## V0 目标

给定一次本地 Git 代码变更，以及可选的审查和证据输入，生成：

- `audit.json`
- `audit.html`

可选生成：

- `audit-feedback.jsonl`（由用户在 `audit.html` 中导出）
- `audit-graph.svg`
- Markdown 摘要或修复清单导出

文档审计样张见 `docs/examples/dogfood-local-repo/`。代码审计主样张见 `docs/examples/hunk-context-demo/`。

## 范围内

- 从本地 Git diff 元数据解析变更文件。
- 提取 finding 相关 hunk snippet，并写入 `finding.hunk`。
- 将 CrossReview `ReviewResult` 作为一种证据源导入。
- 将 findings、evidence 和 fixes 归一化为统一图谱。
- 渲染带代码上下文的本地 HTML 审计视图，不引入前端构建链。
- 在 `audit.html` 中支持 finding 决策采集、localStorage 暂存和 JSONL 导出。
- 可选渲染静态 SVG 概览图 `audit-graph.svg`。
- 可选导出 Markdown 摘要或修复清单。
- 支持一次任务的多轮审计快照，用于表达生成、审查、修复、再审查的收敛过程。

## 范围外

- 直接调用 LLM 做 review。
- 自动修改代码。
- 消费 `audit-feedback.jsonl` 并影响下一轮审计。
- 将用户反馈写回 `audit.json`。
- 全仓库调用图分析。
- 深度语言级 AST 分析。
- 远程 GitHub / GitLab PR URL 输入。
- Hosted service、团队 dashboard 或 policy engine。
- 替代 CrossReview。

## V0 输入

V0 只支持一次本地 Git diff 范围：

```bash
audit-graph build --diff HEAD~1 --crossreview review-result.json --out audit/
audit-graph build --diff main..feature --out audit/
audit-graph build --staged --out audit/
```

远程 PR / commit URL 是后续 adapter 能力，不进入 v0。

## V0 命令

计划命令形态：

```bash
audit-graph build --diff HEAD~1 --crossreview review-result.json --out audit/
audit-graph render --audit audit/audit.json --out audit/
```

`render` 可以根据用户环境生成本地编辑器跳转链接，但这些链接不写入 `audit.json`。

## 实现顺序

V0 采用 renderer-first 路径：先实现 `audit.json -> audit.html`，用手写样例和真实小 diff 验证页面是否可读、finding card 是否好用、反馈导出是否可理解。

`risk_score` 和 `verdict` 在 v0 可以先透传 `audit.json.summary`，或使用简单规则兜底：存在 open high finding 时视为高风险，存在 open finding 时视为 `concerns`，无 open finding 时视为 `pass_candidate`。复杂评分规则不阻塞 renderer 验证。

## audit.html 信息架构

`audit.html` 是 v0 默认人类审计视图，必须围绕用户真实审计动作组织，而不是围绕数据结构堆字段。

基础 section 顺序：

1. 审计结论

展示本轮状态、风险评分、finding 数量、失败证据数量、是否建议继续修复。

2. 变更摘要

展示任务意图、变更范围、影响文件、行为变化和可能的继续优化点。摘要区必须展示摘要审计状态，例如 `verified`、`partial`、`challenged` 或 `unknown`。

3. 问题清单

按 severity 和可操作性排序。每个 finding 使用 card 展示标题、位置、hunk snippet、关键行装饰条、证据、修复入口和用户决策控件。

4. 修复方案

按优先级组织修复建议，包含建议动作、涉及文件、验证方式和当前状态。

5. 多轮对比

展示 run 之间的新增、已修复、仍存在问题，以及风险评分变化。只有一个 run 时可以降级成短提示。

6. 证据详情

展示 CrossReview、test、lint、typecheck、安全扫描等证据来源和原始摘要。

条件 section：

7. 可选概览图

只有当 `audit.json` 中存在 SVG artifact 或实际生成 `audit-graph.svg` 时才渲染。无 SVG 产物时不展示空 section。

## finding 代码上下文

V0 的 finding 使用扁平字段：

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

`hunk` 是 build 阶段提取的 render-ready unified diff snippet。Renderer 可以按行读取该字符串做展示，但不得回头读取 Git。

`highlight_lines` 由 build 或上游 review adapter 提供。Renderer 不应从自然语言描述里猜关键行。

## 交互反馈

V0 的 `audit.html` 支持纯静态交互：

- 标记 `false_positive`
- 标记 `accept`
- 添加 `comment`
- 设置 `severity_override`
- localStorage 暂存
- 导出 `audit-feedback.jsonl`

导出格式为 JSONL，每行一条记录：

```json
{"target_type":"finding","target_id":"finding-001","action":"accept","reason":"确认缓存路径仍有风险","fingerprint":"sha256:...","created_at":"2026-07-08T10:30:00+08:00"}
```

`severity_override` 记录应额外包含 `severity` 字段：

```json
{"target_type":"finding","target_id":"finding-002","action":"severity_override","severity":"low","reason":"测试缺口不是本轮阻塞项","fingerprint":"sha256:...","created_at":"2026-07-08T10:32:00+08:00"}
```

该文件给下一阶段或 LLM 使用。v0 不负责读取该文件并改变审计结果。

## 工作流形态

独立使用：

```text
Git diff
  -> audit-graph
  -> audit.json / audit.html
  -> optional: audit-feedback.jsonl / audit-graph.svg / markdown export
```

嵌入工作流：

```text
develop
  -> review
  -> audit-graph
  -> human audit decision
  -> confirm
  -> finalize
```

这里的 workflow 集成是可选能力，不是产品前提。

## SVG 范围

V0 只定义一种可选 SVG：Audit Graph，文件名为 `audit-graph.svg`。

它不做通用画图，不支持多 diagram type，也不提供多套视觉风格。可以借鉴已有 SVG 技能的工程方法：模板生成、文本转义、XML 校验和可选 PNG 导出。

SVG 的职责是概览，不是完整审计报告。完整的变更摘要、问题详情、修复方案、多轮对比和用户决策采集由 `audit.html` 承担。

节点较多时，SVG 不展开完整详情。渲染器应优先展示 top risks 和汇总节点，完整列表进入 `audit.html`。

## 质量标准

- 最小端到端：给定一个包含 1 个 finding、1 个 evidence、1 个 fix 和一段 hunk 的最小 `audit.json`，renderer 必须输出一张可读 finding card，包含 hunk table、关键行装饰条、证据/修复关联和反馈按钮。
- `audit.json` 是真相源。
- `audit.html` 必须能从 `audit.json` 重新生成。
- `audit.html` 必须能在没有编辑器跳转能力时独立阅读。
- `audit-feedback.jsonl` 必须是结构化、可追加、可被后续工具读取的用户决策记录。
- 若生成 `audit-graph.svg`，它也必须能从 `audit.json` 重新生成。
- 每个可视化风险节点都必须能回连到 finding、evidence 或 changed file。
- 可选输入缺失时应降级输出，而不是阻断渲染。
- 每个审计快照都必须能追溯到对应输入和生成产物。
- SVG 有效性包含两层：XML 有效和审计回链有效。
