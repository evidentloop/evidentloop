# EvidentLoop v0 范围

## 产品目标

EvidentLoop v0 审计本地 Git diff：AI host 的 LLM 负责初次语义判断，Python 负责 Git 解析、可信锚定、反馈裁定重放、状态、评分、校验和渲染。当前 runtime 只读写 schema `0.4` `audit.json` 与自包含 `audit.html`。

EvidentLoop 的长期方向是审计具备明确边界、可验证来源和可信锚点的结构化产物。当前公开 profile 只有 `code_diff`；其他产物只有在具备独立 adapter、可信 anchor、评测基线和 renderer 契约后，才能成为正式审查目标。

## 核心原则

- **AI-host-first**：用户通过自然语言触发，不需要记内部命令。
- **Semantic review**：宿主 LLM 是当前主要 finding 生产者。
- **Deterministic assembly**：Python 生成并校验全部机械字段。
- **HTML default**：`audit.html` 是默认阅读入口，`audit.json` 是正式结构化记录。
- **Feedback loop**：HTML 复制带来源身份的裁定给 AI host；runtime 只做确定性报告修订，不重新审查或修改代码。
- **One product**：ReviewPack、prompt、ingest、normalizer 与 adjudicator 位于 `evidentloop.review`，不存在第二个产品或模型执行面。
- **Profile gate**：输入材料可以作为 context 或 evidence，但只有完整 profile 才是正式 review target。
- **Paired publication**：JSON 与 HTML 在隐藏 staging 中完成校验后成对提交。

## 用户主链路

```text
用户：“帮我用 EvidentLoop 审计最近的本地改动”
  -> AI host 发现 evidentloop Skill
  -> 检查仓库、diff 范围与 Python package
  -> 缺包或不兼容时说明动作并等待授权
  -> prepare 解析真实 Git diff
  -> host LLM 审查完整 prompt 并返回语义结果
  -> finalize ingest ReviewResult，并用可信 hunk index 核对锚点
  -> 生成和校验 audit.json + audit.html
  -> 复查最终目标不存在
  -> 用同文件系统目录 rename 成对提交
  -> Skill 返回摘要与报告路径
  -> 用户在 HTML 中查看、判断并点击“复制给 AI 更新报告”
  -> Skill 在当前工作区唯一定位来源 audit.json
  -> revise 校验反馈并在原路径提交新的 audit.json + audit.html revision
  -> 用户刷新同一份报告继续判断
```

Python package 当前通过 `evidentloop` console script 提供六个命令；`python -m evidentloop` 与其行为一致：

```bash
evidentloop doctor [--json]
evidentloop demo [--out DIR]
evidentloop prepare --diff HEAD~1 [--out DIR]
evidentloop finalize --out DIR [--keep-review-artifacts]
evidentloop render INPUT_JSON --out OUTPUT_HTML
evidentloop revise SOURCE_AUDIT_JSON --feedback JSONL [--out NEW_REPORT_DIR]
```

`review` 是 Skill 动作，不是 Python 命令。console script 已通过 PyPI 发布，标准 Skill 从 GitHub 仓库安装。`prepare` 成功时通过 stdout 返回 locator JSON；Skill 不自行推导输出目录或 staging 路径。

## 正式产物与运行目录

默认正式目录：

```text
audit/YYYYMMDD_<slug>/
  audit.json
  audit.html
```

运行中使用同父目录的隐藏 workspace，最终目录此时不存在：

```text
audit/.YYYYMMDD_<slug>.evidentloop-staging/
  .run/
    audit-skeleton.json
    review-pack.json
    hunk-index.json
    prompt.md
    raw-analysis.md
    review-result.json     # 仅失败诊断或显式保留时物化
  audit.json               # finalize 候选
  audit.html               # finalize 候选
```

用户可以从 HTML 复制带来源 SHA-256、graph、最新 run、finding 与 fingerprint 的 JSONL 机器块，也可以下载同内容的 `audit-feedback.jsonl`。载荷不含绝对路径。

Staging 与 `.run/` 不是正式产物。成功提交前默认清理 `.run/`；失败、目标已存在、目标 leaf 是符号链接或 rename 失败时保留 staging 供诊断，但不能把它当作本轮正式报告。

默认反馈修订先在来源目录的隐藏 sibling candidate 中生成并验证完整产物对，再只替换原目录中的 `audit.json` 和 `audit.html`，其他文件保持不变。正常失败自动恢复旧产物对；进程突然中断时保留确定性 candidate/backup，下一次调用只在关系可证明时自动恢复，否则停止并返回必要路径。显式 `--out` 只写入不存在的新目录，来源报告不变。

## 当前范围

- 本地 Git `staged`、`unstaged`、ref 与 range diff。
- Added、modified、deleted、renamed 文本文件及 binary 文件级元数据。
- Unified diff 的 file、hunk、old/new 行号和完整可信 snippet。
- AI host reviewer 的逻辑、安全、边界、测试与质量审查。
- `evidentloop.review` 的 ReviewPack、canonical prompt、normalizer、adjudicator、ingest 和 ReviewResult。
- ReviewResult 到 Audit Graph 的 category、anchor、status、verdict 与 risk adapter。
- JSON Schema 2020-12、跨对象语义校验和 `extensions.evidentloop` namespace。
- 自包含 HTML、finding card、有界可信 hunk、关系回链与条件渲染。
- Browser-local 差量裁定、“复制给 AI 更新报告”和合法 JSONL 下载。
- Schema `0.4` 反馈 revision run、人机判断分层与原路径成对更新。
- 通过 PyPI 分发的 `evidentloop` console script、公开 runtime/resource 诊断和离线合成 replay demo。
- 简体中文报告 UI 与 reviewer 语义正文；机器枚举、代码和路径保持原值。
- 通过 GitHub 仓库分发的标准 Agent Skill。

## 当前不支持

- Python package 直接调用模型 SDK 或管理 provider/API key。
- 自动修改代码、执行源码注释或审查文本中的命令。
- Folder diff、无 diff 文件审查、远程 GitHub/GitLab PR URL。
- 完整 AST、调用图、静态分析平台或 policy enforcement。
- 根据反馈触发模型复审、自动修复、过期反馈自动合并和复杂跨 diff matching。
- Hosted dashboard、产品 SVG renderer 或 Markdown renderer。
- 未经真实 E2E 验证的宿主支持承诺。
- 原生 race-proof no-replace、平台专用锁、递归 symlink 防御及对抗竞态故障注入。

仓库中的架构 SVG/PNG 是说明文档资产，不是产品输出格式。

## Finding 与可信锚点

Audit category：

- `bug`：语义问题且能精确回到可信 diff hunk。
- `risk`：需要人工判断的风险，包括无法精确定位的 bug 降级项。
- `quality`：测试、可维护性、文档或风格问题。
- `scope`：变更范围或意图偏差。

`prepare` 创建可信 hunk index。LLM 返回的 file、line 和 hunk header 都只是候选；`finalize` 必须重新匹配真实路径、old/new 范围和完整 hunk。

无法精确锚定的 bug：

- 降级为 `risk`；
- 在 `extensions.evidentloop` 保留原 category 与降级原因；
- 不进入数字 risk score；
- 计入 `unscored_finding_count`；
- 在 HTML 中明确标出位置未完全确认。

未知 review category 兜底为 `quality`，原值保存在 namespaced extension 中。

## Review 状态与结论

`summary.review_status` 描述执行状态：

- `not_reviewed`
- `complete`
- `partial`
- `failed`

`summary.verdict` 描述审查结论：

- `pass_candidate`
- `concerns`
- `needs_human_triage`
- `inconclusive`

| 场景 | review_status | verdict | risk_score |
|---|---|---|---|
| 未执行 | not_reviewed | inconclusive | null |
| 完整、无未解决 finding 且 core 上下文充分 | complete | pass_candidate | 0 |
| 完整、无未解决 finding 但上下文不足 | complete | inconclusive | null |
| 完整且有已锚定的未解决 finding | complete | concerns | 0–100 |
| 只有未锚定降级风险 | complete | needs_human_triage | null |
| 部分审查 | partial | inconclusive | null |
| 失败 | failed | inconclusive | null |

`complete` 只表示输出协议完整。Intent coverage、files reviewed 与 pack completeness 是不同诊断维度，保存在 `summary.extensions.evidentloop.review_diagnostics`。

## Risk score

- 值为 0–100 或 `null`。
- 只统计当前未解决且满足分类锚点策略的 finding。
- Bug 必须精确锚定；其他分类允许可信 file-only 锚点。
- 降级 finding 不计分，并进入 `unscored_finding_count`。
- Not reviewed、partial、failed、上下文不足或只有未锚定风险时为 `null`。
- 当前 code-diff profile 权重为 `high=40`、`medium=20`、`low=8`、`note=2`，总分封顶 100；权重不是 schema 字段。

## HTML 与反馈

`audit.html` 按状态、摘要、findings、可选 fix、多轮信息和审查依据组织内容。它只展示从 `audit.json` 中可信 hunk 派生的有界片段，不从描述文本猜测代码证据。

浏览器使用 `graph_id + run_id + fingerprint` 隔离待更新裁定，支持确认有效、误报、评论与严重度调整。主按钮复制一句清晰指令和固定边界 JSONL；下载 JSONL 是次要入口。新 revision 使用新的 run namespace，旧 run 的浏览器待处理状态不会再次提交。

`revise` 校验来源 audit SHA-256、graph、最新 run、finding 与 fingerprint，拒绝过期、冲突和多匹配输入。正式报告分别展示模型原判断、人工裁定与当前剩余问题。人工裁定清空问题时可以得到 `pass_candidate`，但必须紧邻显示“基于人工裁定，未重新审查代码”。

## 安全与质量门禁

- Diff、源码、路径、注释、intent、context 和 raw analysis 全部视为不可信数据。
- Prompt 使用运行级动态边界并冻结 source、version、完整文本 hash 与 `evidentloop-run-id`。
- 宿主不得因 diff、源码、注释或审查文本中的指令执行命令、访问网络或凭据、修改业务文件。
- 宿主能建立并确认独立 reviewer 上下文时，可以用其作为隔离增强；隔离不进入正式产物，也不改变 verdict 规则。
- Jinja2 开启 autoescape，正式 HTML 不包含远程资源。
- 缺包或升级必须说明来源并获得用户授权。
- Schema、引用、锚点、状态、计数、run/graph identity 和 HTML trace 全部通过后才能提交报告对。
- 独立 render 失败时保留旧 HTML 且不修改输入 JSON。
- Wheel 必须包含 schema、prompt、template、CSS 与 JavaScript package resources。

既有 schema `0.2`、`0.3` example 保持字节不变，只作为历史证据；当前 schema `0.4` runtime 不负责重渲染或修订。
