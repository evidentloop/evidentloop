# change-audit `0.2` code-diff 数据模型

## 契约边界

本文定义首个 `code_diff` audit profile 的 `audit.json 0.2`。它是该 profile 的唯一机器真相源，结构由 JSON Schema 2020-12 定义；Python 只补充跨对象引用、hunk anchor 和渲染回链校验。`0.2` 已通过精确语义 bug、显式干净 diff、partial review 和未锚定降级四类流水线 dogfood；它不是所有 artifact 类型的预先通用 schema。

ReviewPack、ReviewResult、staging、`.run/` 和宿主 raw analysis 是内部审查传输，不属于 `audit.json` 公共契约。Renderer 不读取这些中间产物。未来非 diff profile 通过独立 ADR 和 schema 版本增加 review target 与对应 anchor，不在 `0.2` 中预塞空字段。

## 顶层结构

```json
{
  "schema_version": "0.2",
  "graph_id": "audit:example",
  "source": {
    "type": "git_diff",
    "ref": "HEAD~1"
  },
  "runs": [],
  "nodes": [],
  "edges": [],
  "summary": {},
  "extensions": {}
}
```

核心对象拒绝未知字段。Adapter 或宿主诊断数据只能进入 namespaced `extensions`，例如 `extensions.change_audit`。

## 节点类型

| Type | 含义 |
|---|---|
| `run` | 一次审计运行或迭代快照 |
| `change` | 一次 diff、commit、staged set 或 unstaged working-tree change |
| `file` | 一个变更文件 |
| `finding` | 一条语义审查发现 |
| `evidence` | 支持或挑战 finding / claim 的证据 |
| `fix` | 建议修复动作 |
| `artifact` | 由图谱派生的正式产物；不是被审查输入 |

Hunk 不作为公共节点类型。prepare 在内部 `hunk-index.json` 维护可信 hunk；finalize 把 finding 所需的完整 snippet 嵌入 finding。

当前 `artifact` 节点不得复用为 plan/design 等审查目标，否则输入与派生输出语义会冲突。第二种真实 profile 应显式建模 review target。

一期 artifact 节点字段：

- `kind = audit_json | audit_html | audit_feedback_jsonl`
- `path`：派生产物路径
- 可选 `media_type`、`sha256` 和 `extensions`

Artifact 只描述派生输出；`rendered_as` 的目标必须是 artifact，来源必须是非 artifact 的图谱实体。

v0 不把用户反馈建模为节点。反馈由 HTML 导出为独立 JSONL，消费逻辑后续实现。

## 边类型

| Type | 含义 |
|---|---|
| `contains_change` | run 包含 change |
| `supersedes_run` | 新 run 覆盖前一轮 |
| `changes_file` | change 修改 file |
| `finding_in_file` | finding 定位到 file |
| `supported_by_evidence` | evidence 支持 finding |
| `requires_fix` | finding 需要 fix |
| `rendered_as` | 图谱对象被渲染为 artifact |
| `supports_claim` | finding / evidence 支持 summary claim |
| `challenges_claim` | finding / evidence 挑战 summary claim |

语义校验必须检查 ID 唯一、端点存在、端点类型允许，以及 claim ID 属于目标 run/change。

## File

必选字段：

- `id`
- `type = "file"`
- `path`

可选字段：

- `role`
- `change_type = added | modified | deleted | renamed`
- `additions`
- `deletions`
- `extensions`

Renderer 不自行计算缺失的 diff stat。

## Finding

示例：

```json
{
  "id": "finding-001",
  "type": "finding",
  "category": "bug",
  "severity": "high",
  "status": "open",
  "title": "缓存路径仍可能返回过期 token",
  "detail": "缓存命中发生在 refresh 校验之前。",
  "file_path": "src/auth_service.py",
  "hunk_id": "hunk:src/auth_service.py:38:1",
  "start_line": 39,
  "end_line": 39,
  "line_side": "new",
  "highlight_lines": [39],
  "hunk": "@@ -38,10 +38,14 @@\n ...",
  "fingerprint": "sha256:...",
  "extensions": {}
}
```

### 核心字段

| 字段 | 说明 |
|---|---|
| `category` | `bug | risk | quality | scope` |
| `severity` | `high | medium | low | note` |
| `status` | finding 生命周期状态，如 `open | fixed` |
| `file_path` | 相对仓库根目录的可信路径 |
| `hunk_id` | prepare 生成的内部可信 hunk 标识 |
| `start_line / end_line` | finding 的可信行范围 |
| `line_side` | `old | new` |
| `highlight_lines` | HTML 装饰条对应的行号 |
| `hunk` | 从 hunk index 复制的完整可信 snippet；renderer 可按命中行生成有界展示片段，但不得改写该字段 |
| `fingerprint` | 用户反馈和相邻 run 匹配使用的稳定标识 |

定位字段对 `bug` 必须存在并通过锚点校验。Risk、quality 和 scope 允许 file-only；没有可信文件时不得生成 `finding_in_file` 边。

### 可信 Hunk

prepare 解析完整 Git diff，建立内部 hunk index：

```json
{
  "hunk_id": "hunk:src/auth_service.py:38:1",
  "file_path": "src/auth_service.py",
  "old_start": 38,
  "old_count": 10,
  "new_start": 38,
  "new_count": 14,
  "header": "@@ -38,10 +38,14 @@",
  "snippet": "@@ -38,10 +38,14 @@\n..."
}
```

LLM 返回的 file、line 和 `@@ ... @@` header 都只是候选锚点。finalize 必须：

1. 规范化并匹配真实变更文件；
2. 确认 header 存在于该文件；
3. 确认 line 落入 old/new 或上下文范围；
4. 从索引复制完整 hunk；
5. 生成可信 hunk ID、line side、range 和 highlight。

Header 与 line 冲突时视为未锚定。不得把 LLM 返回的 hunk 文本直接写入正式 `audit.json`。

### Bug 降级

语义 bug 无法精确锚定时，保留为未计分 risk：

```json
{
  "category": "risk",
  "severity": "medium",
  "extensions": {
    "change_audit": {
      "original_category": "logic_error",
      "downgraded_from": "bug",
      "downgrade_reason": "line_outside_trusted_hunk"
    }
  }
}
```

规则：

- 不静默丢弃。
- severity 最高为 `medium`。
- 不进入数字 risk score。
- 计入 `summary.unscored_finding_count`。
- HTML 显示“语义发现，位置未完全确认”。

### Category 映射

| Review category | Audit category |
|---|---|
| `bug`, `logic_error`, `semantic_equivalence`, `correctness` | bug 候选 |
| `security`, `performance`, `possible_bug`, `missing_validation`, `error_handling` | risk |
| `missing_test`, `quality`, `maintainability`, `suggestion`, `style`, `documentation`, `testing` | quality |
| `scope`, `spec_mismatch` | scope |
| 未知或 `other` | quality |

原始值始终可写入 `extensions.change_audit.original_category`。Bug 候选只有在 plausible 且精确锚定后才能保留 `bug`。

### Fingerprint

推荐输入：

```text
schema_version
+ normalized file_path
+ normalized audit category
+ trusted hunk_id or stable file anchor
+ normalized title
```

输出格式：`sha256:<hex>`。

同一 run 内必须唯一；相邻 run 在锚点未大幅变化时应大概率可匹配。Fingerprint 由 Python 生成，LLM 不提供。

## Evidence 与 Fix

Evidence 描述审查依据，而不是用 `finding.origin` 复制来源。

示例来源：

- `host_llm`
- `test`
- `lint`
- `typecheck`
- `security_scan`
- 后续 `deterministic_rule`

ReviewResult finding 转为 Audit Graph 时，adapter 至少生成一条 host review evidence，并通过 `supported_by_evidence` 连接 finding。Fix 是建议动作；没有可靠修复建议时可以不生成 fix。

## Review Status 与 Verdict

顶层 `summary` 同时保存执行状态和结论，但两者不互相替代。

### review_status

- `not_reviewed`：宿主审查根本没有执行。
- `complete`：审查输出通过完成门禁。
- `partial`：输出截断或只覆盖部分范围。
- `failed`：已尝试审查，但发生拒绝、解析失败或完成门禁失败。

### verdict

- `pass_candidate`
- `concerns`
- `needs_human_triage`
- `inconclusive`

映射：

| 场景 | review_status | verdict |
|---|---|---|
| 未执行 | not_reviewed | inconclusive |
| 完整、无未解决 finding 且 core 上下文门禁通过 | complete | pass_candidate |
| 完整、无未解决 finding 但 core 上下文不足 | complete | inconclusive |
| 完整且有未解决、已锚定 finding | complete | concerns |
| 只有未锚定降级风险 | complete | needs_human_triage |
| 部分审查 | partial | inconclusive |
| 失败 | failed | inconclusive |

ReviewResult 的 intent coverage、files reviewed / total、pack completeness 和原始 failure reason 属于不同诊断维度，进入 `summary.extensions.change_audit.review_diagnostics`，不新增含糊的核心 coverage 字段。

## Summary

必选字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `review_status` | string | 审查执行状态 |
| `verdict` | string | 审查结论 |
| `risk_score` | integer 或 null | 0–100 的已验证风险分 |
| `finding_count` | integer | 全部 finding |
| `open_finding_count` | integer | 当前未解决 finding |
| `unscored_finding_count` | integer | 因锚点降级而未计分的未解决 finding |
| `fix_count` | integer | fix 总数 |

可选字段：

- `fix_done_count`
- `summary_audit_status`
- `risk_delta`
- `extensions`

最小未审查 summary：

```json
{
  "review_status": "not_reviewed",
  "verdict": "inconclusive",
  "risk_score": null,
  "finding_count": 0,
  "open_finding_count": 0,
  "unscored_finding_count": 0,
  "fix_count": 0
}
```

完整干净审查：

```json
{
  "review_status": "complete",
  "verdict": "pass_candidate",
  "risk_score": 0,
  "finding_count": 0,
  "open_finding_count": 0,
  "unscored_finding_count": 0,
  "fix_count": 0
}
```

所有 count、status、verdict 和 score 都由 Python 生成并与节点状态交叉校验，LLM 不直接提供这些机械字段。

## Risk Score

- 只统计当前未解决且通过分类锚点策略的 finding；bug 需要精确 hunk，其他分类允许可信 file-only 锚点。
- 输出范围为 0–100 或 `null`。
- 未锚定降级 finding 不计分，并计入 `unscored_finding_count`；partial/failed 不会因此把全部 finding 计入该计数。
- 只有未锚定风险时：`risk_score = null`、verdict 为 `needs_human_triage`。
- not reviewed、partial、failed 或资料不足时为 `null`。
- 同时存在计分 finding 和未计分 finding 时，保留分数并显示 unscored count。
- severity 权重在 Wave 2 四类流水线 dogfood 后冻结为 `high=40`、`medium=20`、`low=8`、`note=2`，总分封顶 100；权重不是 schema 字段。

`ReviewResult.quality_metrics` 是运行诊断，不能用于 risk score。

## 摘要审计

变更摘要属于 run 或 change 字段，不是节点类型：

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
        "text": "过期 token 不再返回",
        "status": "challenged"
      }
    ]
  }
}
```

Finding 或 evidence 通过 `supports_claim` / `challenges_claim` 边引用目标 change/run 和 `claim_id`。

## 用户反馈

`audit-feedback.jsonl` 不属于 `audit.json`。每行是一条用户动作：

```json
{"target_type":"finding","target_id":"finding-001","action":"false_positive","fingerprint":"sha256:...","graph_id":"audit:example","run_id":"run-001","created_at":"2026-07-10T10:30:00+08:00"}
```

Action：

- `accept`
- `false_positive`
- `comment`
- `severity_override`

`severity_override` 额外包含 `severity`。一期只导出，不消费、不写回图谱。

浏览器状态按 `graph_id + run_id + fingerprint` 隔离；同一动作重复保存只保留最新值，空评论会移除已有评论。导出时每个有效 disposition、非空评论和严重度调整各占一行，特殊字符由 JSON 序列化保真。

## Renderer 边界

Renderer 只消费完整 `audit.json`：

- 不读取 Git。
- 不读取 ReviewPack、ReviewResult、prompt 或 raw analysis。
- 不从描述文本猜测 hunk、highlight、关系或状态。
- finding 的代码证据必须来自 `audit.json` 中由可信 hunk index 复制的完整 hunk；HTML 按命中行渲染有界可信片段，以接近 diff2html 的双行号表格明确区分 context/add/delete、突出命中行并标记省略。普通 `<pre>` 不能替代可信 diff hunk，完整长 hunk也不应在每张 finding 卡中重复展开。
- 对业务文本统一转义。
- HTML 中出现的 `data-node-id` / `data-edge-id` 必须指向真实图实体；每个 finding/fingerprint、claim、anchored hunk 和 feedback target 还必须反向证明已经渲染。未进入当前阅读视图的关系边不伪造可视回链。

HTML 回链校验：

| 属性 | 规则 |
|---|---|
| `data-node-id` | 存在于 nodes 或 runs |
| `data-edge-id` | 存在于 edges |
| `data-claim-id` | 存在于目标 run/change claims |
| `data-fingerprint` | 等于对应 finding fingerprint |
| `data-feedback-for` | 指向 finding |

结构、引用、锚点或回链失败时阻止整个正式 JSON/HTML 产物对提交。可选展示字段缺失时允许明确降级。独立 `render` 命令只重建一个 HTML，不受 finalize 目录提交约束。

## 多轮审计

`run` 表示审计快照，`supersedes_run` 表示后一轮覆盖前一轮。

```text
run-001: 初次审查，存在 concerns
run-002: 修复后仍有部分 finding
run-003: 完整审查且无未解决 finding；上下文充分时 pass_candidate，不足时 inconclusive
```

复杂 diff matching、反馈消费和跨大规模重构稳定 fingerprint 进入后续版本。
