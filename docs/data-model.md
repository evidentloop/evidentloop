# EvidentLoop `0.5` code-diff 数据模型

## 契约边界

本文定义当前 `code_diff` profile 的 `audit.json` 公共契约。结构由 JSON
Schema 2020-12 校验，Python 另外校验跨对象引用、可信 hunk、summary、
feedback revision、fix verification provenance 与 HTML 回链。

Canonical schema URI：
`https://evidentloop.github.io/evidentloop/schemas/audit-v0.5.schema.json`。
Runtime 只接受 `0.5`；`0.4` 及更早报告保持历史只读，不能 render、revise
或作为 fix verification 来源，需用当前 runtime 重新生成。没有兼容 reader、
迁移器或双写。

ReviewPack、ReviewResult、staging、`.run/`、raw analysis 和反馈 JSONL
是内部传输，不属于 `audit.json`。Renderer 只读取通过校验的正式 JSON。

## 顶层结构与版本

```json
{
  "schema_version": "0.5",
  "graph_id": "audit:example",
  "source": {"type": "git_diff", "ref": "HEAD~1"},
  "runs": [],
  "nodes": [],
  "edges": [],
  "summary": {},
  "extensions": {
    "evidentloop": {
      "diff_version": "sha256:..."
    }
  }
}
```

- `diff_version`：本次实际 Git diff 的内容版本，保存在
  `extensions.evidentloop.diff_version`。
- `report_version`：正式 `audit.json` 原始字节的内容版本，只由命令/API
  返回，不写入自身。
- 两者都必须使用 `sha256:<64 lowercase hex>`。
- 核心对象拒绝未知字段；扩展数据只能进入 namespaced `extensions`。

## 图实体

节点类型：

| Type | 含义 |
|---|---|
| `run` | 一次模型审查或同 diff 人工修订 |
| `change` | 当前 diff |
| `file` | 一个变更文件 |
| `finding` | 一条审查问题 |
| `evidence` | 支持 finding 或 fix claim 的证据 |
| `fix` | 建议修复动作 |
| `artifact` | 由图谱派生的正式产物 |

边类型：

| Type | 含义 |
|---|---|
| `contains_change` | run 包含 change |
| `supersedes_run` | 新 run 覆盖前一轮 |
| `changes_file` | change 修改 file |
| `finding_in_file` | finding 定位到 file |
| `supported_by_evidence` | evidence 支持 finding |
| `requires_fix` | finding 需要 fix |
| `rendered_as` | 图实体渲染为 artifact |
| `supports_claim` | evidence/finding 支持 fix claim |
| `challenges_claim` | evidence/finding 挑战 fix claim |

语义校验检查 ID 唯一、端点存在、允许的端点类型以及 claim 归属。

## Finding 与可信锚点

Finding 的核心字段：

- `category`: `bug | risk | quality | scope`
- `severity`: `high | medium | low | note`
- `status`: `open | fixed | dismissed`
- `title`、`detail`、`fingerprint`
- `model_judgment`：初次模型的 status/severity，不随人工裁定改写
- 可选 `human_adjudication`：当前人工 disposition、评论、severity override
  与 applied run
- 可信定位存在时包含 `file_path`、`hunk_id`、`start_line`、`end_line`、
  `line_side`、`highlight_lines` 和完整 `hunk`

`prepare` 从真实 Git diff 建立 hunk index。LLM 返回的路径、行号和 hunk
header 只是候选；`finalize` 必须反查真实文件和范围，再复制完整可信 hunk。
无法精确锚定的 bug 保留为 `risk`，在扩展中记录
`downgraded_from = "bug"` 与 `downgrade_reason`，severity 最高为 `medium`。

Fingerprint 由 Python 根据 schema、规范化路径、category、可信锚点和标题
生成；同一 run 内唯一，格式为内容版本。LLM 不提供 fingerprint。

## Summary：状态、结论与严重程度

`review_status` 与 `verdict` 分开表达：

- `review_status`: `not_reviewed | complete | partial | failed`
- `verdict`: `pass_candidate | concerns | needs_human_triage | inconclusive`

必选 summary 字段：

| 字段 | 说明 |
|---|---|
| `review_status` | 审查是否完整执行 |
| `verdict` | 当前审查结论 |
| `overall_severity` | 当前有效 open finding 的最高严重度；无 open 或审查不完整为 `null` |
| `finding_count` | finding 总数 |
| `open_finding_count` | 当前 open finding 数 |
| `fix_count` | fix 总数 |
| `basis` | `model_review` 或 `human_adjudication` |

可选字段包括 `fix_done_count`、`summary_audit_status`、`model_verdict`、
`model_overall_severity`、`notice` 与 `extensions`。

完整审查中通常按 open finding 得出：

- 没有 open finding：`pass_candidate`
- 存在一般 open finding：`concerns`
- 所有 open finding 都由 bug 降级或缺少可信文件关联：`needs_human_triage`

输入或模型结论不足时，完整审查也可以是 `inconclusive`；若仍有 open
finding，`overall_severity` 继续由这些 finding 计算。非完整审查始终为
`inconclusive`，且 `overall_severity` 为 `null`。

HTML 将 `pass_candidate` 显示为“无待处理问题”。它只表示当前报告没有
open finding，不代表代码已经获准合并、发布或上线。

`overall_severity`、verdict 和 finding severity 是不同语义，不互相替代。
Schema `0.5` 不包含风险分、风险 delta、替代分值或“是否计分”字段。

## 变更摘要与 fix claim

模型审查可以把语义化变更摘要写入现有 change 节点：

- 主 change 的 `summary` 保存总体变化，`extensions.evidentloop.review_focus`
  保存本轮最值得核验的边界；
- 1–5 个附属 change 分别保存模型按实现逻辑选择的主题，`title` / `summary`
  说明行为变化，`extensions.evidentloop.impact` 说明影响范围；
- 文件统计和 `changes_file` 关系仍归属于主 change，完整文件列表不被主题拆分。

若语义摘要缺失或格式无效，生成链路继续使用确定性的主 change 和文件统计；
它不会改变 findings、verdict 或严重程度，但审查完成状态为 `partial`。

Change/run 也可以包含：

```json
{
  "summary": "修复 token refresh 过期处理",
  "summary_audit": {
    "status": "partial",
    "claims": [
      {
        "id": "claim-001",
        "text": "过期 token 不再返回",
        "status": "challenged",
        "reason": "旧缓存分支仍先于失效判断返回"
      }
    ]
  }
}
```

Claim status 真值表：

| supports edge | challenges edge | status |
|---|---|---|
| 有 | 无 | `supported` |
| 无 | 有 | `challenged` |
| 有 | 有 | `partial` |
| 无 | 无 | `unknown` |

每个 claim 必须有非空 `reason`。没有 claim 时 summary audit 为
`not_audited`；全部同态时取该状态；混合时为 `partial`。该技术汇总不替代
当前 verdict 或 `overall_severity`。

Claim 的 status、reason 和 Evidence 引用都属于当前 `model_review` 判断，来源
保留为 `host_llm`。`complete` 表示协议要求的输出齐全，不表示 EvidentLoop 已把
模型引用转换为确定性测试证据或独立证明其语义为真。

HTML 保留 claim 的模型原判断。若它关联的 finding 已全部被忽略或修复，页面只在
派生展示中显示“模型原判断：认可/不认可/部分认可/暂无法判断”和
“当前裁定：相关问题已忽略/修复”，并使用中性配色；claim、edge 和 finding 数据
本身不被改写。变更文件入口同样按当前 finding 状态显示
“查看待处理/已忽略/已修复问题”。

## Fix verification provenance

只有显式选择旧报告中当前仍为 open 的 finding，才能验证新 diff 是否支持
用户的修复声明。当前报告保存最小一跳来源：

```json
{
  "extensions": {
    "evidentloop": {
      "fix_verification": {
        "version": 1,
        "source_report_version": "sha256:...",
        "source_diff_version": "sha256:...",
        "targets": [
          {
            "claim_id": "claim-001",
            "finding_id": "finding-001",
            "fingerprint": "sha256:...",
            "source_title": "旧 token 仍可能被返回",
            "claim": "缓存路径已改为先失效再读取"
          }
        ]
      }
    }
  }
}
```

该对象拒绝缺失、未知或重复字段/目标。它不保存绝对路径、旧 runs、claim
结果、当前 verdict、当前严重程度或当前 diff identity。连续验证只引用直接
前驱，不扫描目录或建立 series/registry。

新报告的 `runs` 只包含当前 diff 的 `model_review` 和之后同 diff 的
`feedback_revision`。旧报告原始字节保持不变。

## 用户反馈与 revision

`audit-feedback.jsonl` 不属于 audit schema。每条事件绑定
`graph_id + run_id + fingerprint + source_audit_sha256`，action 为：

- `accept`
- `false_positive`
- `comment`
- `severity_override`

Run 链路顺序是权威顺序；`created_at` 只用于展示。`comment: null` 删除评论，
`severity: null` 恢复模型严重度。误报只让该 finding 暂时不参与当前结论，
不会删除 severity override；以后重新确认有效时该 override 可以再次生效。

每次有效修订追加一个 `feedback_revision` run，不重新审查代码。人工 summary
保留 `model_verdict`、`model_overall_severity`，并显示
`notice` 固定为“报告已按人工裁定更新；未重新审查代码，模型原判断仍保留。”；无语义变化不会生成空 revision。

HTML 历史按权威 run 顺序显示问题标题和用户动作，只列出实际变化的 verdict、
overall severity 与 open finding 数；三者未变化时明确写“报告结论未变化”。
删除评论与恢复模型严重度使用不同文案，不把两种 null 都写成“恢复默认”。

HTML 将 `requires_fix` 关联的建议直接显示在对应问题卡片中，不再另建修复建议
区块或重复展示 fix 状态。fix 节点与关联边继续保留在 JSON 和 HTML 追溯属性中。
HTML 不展示 `bug / risk / quality / scope` 这组宽泛 category 徽标；具体问题类型
由标题和原因表达，category 继续保留在 JSON 与 `data-category` 中。
`dismissed` 问题仍保留原始严重度、原因、建议和 diff，但卡片边线、严重度徽标和建议区
使用中性配色，避免被误读为当前仍需处理的问题；正文不整体降透明度。

## Renderer 边界

Renderer：

- 只消费完整、有效的 `audit.json`
- 不读取 Git、ReviewPack、raw analysis 或旧报告
- 不从描述文本猜测锚点、关系或状态
- 对业务文本统一转义
- 只从可信完整 hunk 生成一个有界单栏 diff 节选
- 长行不折行；长 hunk 只在局部容器双向滚动
- 只渲染有数据的 fix verification、finding、feedback history，以及 finding
  内关联的 fix 建议

正式输出前必须通过 schema、语义、锚点和 `data-*` 回链校验。独立
`render` 失败时不得替换已有 HTML，也不修改输入 JSON。
