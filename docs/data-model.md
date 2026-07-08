# audit-graph 数据模型

## 核心对象

审计图谱是一个有类型的有向图。节点表示审计实体，边表示证据关系。

`audit.json` 是唯一真相源。`audit.html`、`audit-graph.svg` 和 Markdown 导出都必须能从 `audit.json` 或同一份内存图谱对象生成。

## 节点类型

| Type | 含义 |
| --- | --- |
| `run` | 一次审计运行或一次任务迭代快照 |
| `change` | 一次 diff、commit、staged set 或 unstaged working-tree change |
| `file` | 一个变更文件 |
| `finding` | 一条审查发现或确定性规则发现 |
| `evidence` | 测试、lint、typecheck、scan 或外部证据项 |
| `fix` | 一个建议修复动作 |
| `artifact` | `audit.html`、`audit-graph.svg`、Markdown 导出等生成产物 |

v0 不把用户反馈建模为图谱节点。`audit.html` 可以采集用户决策并导出 `audit-feedback.jsonl`，但反馈消费、`user_decision` 节点和相关边进入后续版本。

## 边类型

| Type | 含义 |
| --- | --- |
| `contains_change` | 一次 run 包含一次 change |
| `supersedes_run` | 一次 run 是对前一次 run 的修复或再审计 |
| `changes_file` | 一次变更修改了一个文件 |
| `finding_in_file` | 一条 finding 定位在某个文件中 |
| `supported_by_evidence` | 某条 evidence 支持或解释一条 finding |
| `requires_fix` | 一条 finding 需要一个 fix |
| `rendered_as` | 某个图谱对象被渲染成输出产物 |
| `supports_claim` | 某条 evidence 或 finding 支持 `change` / `run` 中的一条摘要声明 |
| `challenges_claim` | 某条 finding 或 evidence 挑战 `change` / `run` 中的一条摘要声明 |

## finding 定位与代码上下文

v0 的 `finding` 使用扁平字段。这样 renderer 和其他消费者可以直接读取常用字段，同时保留后续扩展到远程 commit、完整 diff 或结构化 hunk 的空间。

示例：

```json
{
  "id": "finding-001",
  "type": "finding",
  "severity": "high",
  "status": "open",
  "title": "旧 token 仍可能被缓存层返回",
  "detail": "get_token 在调用 refresh 前会先查缓存，旧 token 仍可能被返回。",
  "file_path": "src/auth_service.py",
  "start_line": 38,
  "end_line": 52,
  "line_side": "new",
  "highlight_lines": [39, 40, 41],
  "hunk": "@@ -38,10 +38,14 @@\n     def get_token(...)\n...",
  "fingerprint": "sha256:..."
}
```

字段约定：

| 字段 | 说明 |
| --- | --- |
| `file_path` | 相对仓库根目录的文件路径 |
| `start_line` / `end_line` | finding 相关代码范围 |
| `line_side` | 行号所在侧，v0 可用 `new`，删除行或远程 diff 可用 `old` |
| `highlight_lines` | renderer 应加装饰条的关键行号 |
| `hunk` | build 阶段提取的 render-ready unified diff snippet |
| `fingerprint` | 简化稳定标识，用于后续反馈匹配和多轮追踪 |

`hunk` 必须由 adapter 或 build 阶段从 Git diff 提取。Renderer 只消费 `audit.json`，不得回头读取 Git、CrossReview 或原始审查文本。

`hunk` 是用于 HTML 展示的代码上下文，不是完整 diff 存储。v0 默认只嵌入 finding 附近的 snippet。完整文件 diff、远程 PR 链接或结构化 hunk line 数组是后续扩展，不进入 v0 schema。

### Hunk 行号规则

Renderer 可以读取 `hunk` 字符串并生成 HTML code table。行号规则必须来自 unified diff header，而不是重新读取 Git。

示例 header：

```diff
@@ -38,10 +38,14 @@
```

解析规则：

- 从 `-38,10` 得到 old side 起始行号 `old_line = 38`。
- 从 `+38,14` 得到 new side 起始行号 `new_line = 38`。
- 以 `+` 开头的行使用 `new_line`，然后 `new_line += 1`。
- 以 `-` 开头的行使用 `old_line`，然后 `old_line += 1`。
- 以空格开头或无 diff 符号的上下文行两侧都存在，展示时可使用 `new_line`，然后 `old_line += 1` 且 `new_line += 1`。
- header 行本身不展示为代码行。

如果 `line_side` 是 `old`，定位和 `highlight_lines` 解释为 old side 行号；否则解释为 new side 行号。

### Hunk 重复规则

v0 允许多个 finding 各自携带相同或重叠的 `hunk` snippet。Renderer 不需要做 hunk 去重，也不需要引入 `hunk_id`。

这样会在 HTML 中重复展示同一段代码，但换来更简单的 finding card 渲染和更独立的审计上下文。后续如果大变更下重复过多，再引入共享 hunk 引用。

### Fingerprint 规则

`fingerprint` 是简化稳定标识，用于用户反馈匹配和多轮追踪。v0 不追求跨大规模重构稳定，只要求同一轮内唯一、相邻两轮大概率可匹配。

推荐算法：

```text
sha256(file_path + ":" + source_or_rule + ":" + anchor_line_content)
```

字段来源：

- `file_path`：finding 的相对文件路径。
- `source_or_rule`：CrossReview rule id、确定性规则名，或上游 finding source。
- `anchor_line_content`：最能代表 finding 的关键行内容，优先取 `highlight_lines` 的第一行。

输出格式建议为 `sha256:<hex>`。样例中可使用可读占位值，但实现应生成真实 hash。

## 本地跳转链接

`audit.json` 不保存 `vscode://`、`file://` 或远程代码平台 URL。这些链接依赖用户编辑器、仓库绝对路径、浏览器权限和运行环境，应由 renderer 在生成 `audit.html` 时根据配置生成。

`audit.json` 只需要保存 `file_path`、`start_line`、`end_line` 和 `line_side`。即使跳转链接不可用，`audit.html` 也必须能依靠 hunk snippet 独立阅读。

## 用户反馈导出

v0 的 `audit.html` 可以采集用户对 finding 的决策，并导出 `audit-feedback.jsonl`。该文件不是 `audit.json` 的一部分，消费逻辑进入后续版本。

每行是一条独立反馈记录：

```json
{"target_type":"finding","target_id":"finding-001","action":"false_positive","reason":"缓存层已有统一刷新保障","fingerprint":"sha256:...","created_at":"2026-07-08T10:30:00+08:00"}
```

v0 action 枚举：

| action | 含义 |
| --- | --- |
| `false_positive` | 用户认为该 finding 不是问题 |
| `accept` | 用户确认该 finding 是问题，需要修复 |
| `comment` | 用户补充上下文或审计意见 |
| `severity_override` | 用户调整严重度 |

通用字段：

| 字段 | 含义 |
| --- | --- |
| `target_type` | v0 固定为 `finding` |
| `target_id` | 被反馈的 finding id |
| `action` | 用户动作 |
| `reason` | 用户填写的理由或评论 |
| `fingerprint` | finding fingerprint，用于后续匹配 |
| `created_at` | 反馈生成时间，ISO 8601 字符串 |

`severity_override` 应额外包含 `severity` 字段：

```json
{"target_type":"finding","target_id":"finding-002","action":"severity_override","severity":"low","reason":"测试缺口不是本轮阻塞项","fingerprint":"sha256:...","created_at":"2026-07-08T10:32:00+08:00"}
```

后续版本可以读取 `audit-feedback.jsonl`，生成 `user_decision` 节点或其他审计关系。

## 摘要审计

变更摘要必须可审计，但 `summary` 不是节点类型。

摘要属于 `change` 或 `run` 的字段，例如：

```json
{
  "id": "change-001",
  "type": "change",
  "summary": "修复 token refresh 过期处理",
  "summary_audit": {
    "status": "partial",
    "claims": [
      {
        "id": "claim-001",
        "text": "修复 token refresh 过期处理",
        "status": "challenged"
      }
    ]
  }
}
```

审计关系通过边表达：

```json
{
  "id": "edge-claim-001",
  "type": "challenges_claim",
  "from": "finding-001",
  "to": "change-001",
  "claim_id": "claim-001"
}
```

这样可以审计“变更摘要是否准确”，又不会把页面展示块污染成图谱节点类型。

## 最小 `audit.json`

```json
{
  "schema_version": "0.2-alpha",
  "graph_id": "audit:example",
  "source": {
    "type": "git_diff",
    "ref": "HEAD~1"
  },
  "runs": [
    {
      "id": "run-001",
      "label": "initial audit",
      "status": "complete"
    }
  ],
  "nodes": [],
  "edges": [],
  "summary": {
    "risk_score": 0,
    "finding_count": 0,
    "fix_count": 0
  }
}
```

## summary 字段

`summary` 是 `audit.json` 顶层聚合字段，不是节点类型。

必选字段：

| 字段 | 说明 |
| --- | --- |
| `risk_score` | 本轮风险评分 |
| `finding_count` | finding 总数 |
| `fix_count` | fix 总数 |

可选字段：

| 字段 | 说明 |
| --- | --- |
| `open_finding_count` | 未关闭 finding 数 |
| `fix_done_count` | 已完成 fix 数 |
| `summary_audit_status` | 摘要审计状态 |
| `verdict` | 本轮结论 |
| `risk_delta` | 相对前一轮的风险变化，多轮审计时可选展示 |

## Adapter 边界

Adapter 负责把外部输入转换成图谱节点和边。

`auditgraph.adapters.gitdiff` 负责读取 Git diff 元数据、变更文件、finding 相关 hunk snippet 和必要行号信息。`auditgraph.adapters.crossreview`、`auditgraph.adapters.evidence` 负责把外部审查结果和确定性证据导入统一图谱。

## Renderer 边界

Renderer 只消费 `audit.json` 或内存中的归一化图谱对象。它不负责读取 Git、调用 CrossReview、解释 Markdown 或从自然语言推断节点。

所有 renderer 必须在可视元素中保留 `data-node-id` / `data-edge-id`，确保能从产物回到 `audit.json`。

HTML renderer 示例：

```html
<div class="finding-card" data-node-id="finding-001" data-node-type="finding" data-severity="high">
```

SVG renderer 示例：

```xml
<g id="svg-node-finding-001" data-node-id="finding-001" data-node-type="finding">
```

边也应保留来源：

```xml
<path id="svg-edge-001" data-edge-id="edge-001" data-edge-type="supported_by_evidence" />
```

Renderer 可以从 edges 构建反向查找（例如从 finding 找关联 fix），但不可以自己回去解析原始输入。

## 产物边界

`audit.json` 是唯一真相源。`audit.html` 是默认人类审计视图。`audit-graph.svg` 是可选概览图。Markdown 不是默认产物，只作为摘要或修复清单的导出格式。

Renderer 之间不能互相依赖：

```text
audit.json -> audit.html
audit.json -> audit-graph.svg
audit.json -> markdown export
```

不能出现：

```text
audit.html -> audit-graph.svg
audit.html -> fixes.md
```

## 多轮审计

一次 AI coding 任务可以反复优化。数据模型用 `run` 表示每一轮审计快照，用 `supersedes_run` 表示后一轮修复或再审计覆盖前一轮。

示例：

```text
run-001: 初次生成，发现 5 个问题
run-002: 修复后，剩余 2 个问题
run-003: 再审计通过，进入 confirm / finalize
```
