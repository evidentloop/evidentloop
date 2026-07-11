# change-audit v0 范围

## 产品目标

`change-audit` v0 面向本地 Git 变更，使用 AI host 已有的 LLM 做语义审查，再由 Python 生成可校验的 `audit.json` 和自包含 `audit.html`。本文件刻意定义第一个 `code_diff` audit profile；仓库长期 review 内核是 artifact-general，Git diff 不是永久产品边界。

核心原则：

- AI-host-first：用户通过自然语言触发，不需要记内部命令。
- semantic-review-first：宿主 LLM 是一期主要 finding 生产者。
- deterministic-assembly：Python 只做 Git 解析、机械字段、锚点、状态、评分、校验和渲染。
- HTML-first：`audit.html` 是默认人类入口。
- feedback-capture：一期采集用户决策，不消费反馈。
- one-product：CrossReview 合并为内部 `change_audit.review`，不是第二个用户产品。
- profile-gated：非 diff 类型只有具备 adapter、可信 anchor、eval baseline 和 renderer profile 后，才公开正式 audit 能力。
- paired-publication：JSON/HTML 在同父目录隐藏 staging 中完成全部校验；提交前复查最终目标 leaf 不存在，再用同文件系统目录 rename 成对提交。

## 一期分层

1. **Wave 0A — Baseline**

   记录 CrossReview 的 commit、版本、测试、prompt 和 eval 基线。

2. **Wave 0B — Migration**

   等价迁入 `change_audit.review`，不混入 adapter 或 renderer 新行为。

3. **Wave 1 — Schema + Renderer**

   完成 JSON Schema、语义校验、`render_audit_file()`、`render` 和完整 HTML renderer。

4. **Wave 2 — Host Review Integration**

   完成 prepare、隐藏运行上下文、宿主 LLM、finalize、adapter、可信 hunk 和状态映射。通过真实 dogfood 后冻结 schema `0.2`。

5. **Wave 3 — Human Decision**

   完成 localStorage 和 `audit-feedback.jsonl` 导出。

6. **Wave 4 — AI Host Discovery**

   完成自包含 Skill 与 Codex dogfood；QoderCLI 验证 Skill discovery，模型级 smoke 由用户后续手工完成。

## 用户主链路

```text
用户：“帮我用 change-audit 审计最近的本地改动”
  -> AI host 发现 change-audit Skill
  -> 检查仓库、diff 范围和 Python 包
  -> 缺包时说明来源并等待安装授权
  -> prepare 解析真实 Git diff
  -> host LLM 在隔离上下文中分析语义问题
  -> finalize 在隐藏 staging 中解析 ReviewResult、校验锚点、生成 Audit Graph
  -> 生成并校验候选 audit.json + audit.html
  -> 复查最终目标 leaf 不存在
  -> 用同文件系统目录 rename 成对提交最终目录
  -> Skill 返回摘要和报告路径
  -> 用户在 HTML 中查看并导出反馈
```

用户感知是一条动作。Python 包暴露三个入口；正常 Skill 主链调用 `prepare` 和 `finalize`，后者自动渲染，`render` 用于独立重建 HTML：

```bash
python -m change_audit prepare --diff HEAD~1 [--out DIR]
python -m change_audit finalize --out DIR [--keep-review-artifacts]
python -m change_audit render INPUT_JSON --out OUTPUT_HTML
```

`review` 是 Skill 的用户动作，不是 Python 命令。后续可以增加正式 `change-audit` console-script，但永久保留模块入口。

prepare 成功时通过 stdout 返回 `run_id`、`final_dir`、`staging_dir` 的 locator JSON，诊断写 stderr；Skill 不自行推导目录。独立 `render --out` 只原子替换指定 HTML，失败时保留旧 HTML 且不修改输入 JSON。

## 一期产物

默认：

```text
audit/YYYYMMDD_<slug>/
  audit.json
  audit.html
```

运行中或诊断时使用同父目录隐藏 workspace，最终目录此时不存在：

```text
audit/.YYYYMMDD_<slug>.change-audit-staging/
  .run/
    audit-skeleton.json
    review-pack.json
    hunk-index.json
    prompt.md
    raw-analysis.md
    review-result.json     # 仅失败或显式保留时需要物化
  audit.json               # finalize 候选
  audit.html               # finalize 候选
```

用户在 HTML 中主动导出后可以得到 `audit-feedback.jsonl`。浏览器下载位置不保证等于审计目录。

Staging 与 `.run/` 不是用户产物契约：成功提交前默认清理 `.run/`，复查最终目标 leaf 不存在后再把 staging 目录 rename 为最终目录；提交前失败、目标已存在或 rename 失败时保留 staging 并报告路径。ReviewPack 与 ReviewResult 只在内部版本化。

可归一化的宿主拒绝或审查失败可以输出明确的 failed JSON/HTML；schema、安全、路径、不可读写或写入硬失败返回非零。新目标不写正式产物并保留 staging 诊断；提交检查时已有目标或目标 leaf 是符号链接则拒绝，rename 失败也不得冒充本轮结果。

## 范围内

- 本地 Git diff 与显式 diff spec。
- added、modified、deleted、renamed 文本文件及 binary 文件级元数据。
- unified diff 的文件、hunk、old/new 行号和完整 snippet；完整 snippet 保留在 `audit.json`，HTML finding 只展示命中附近的有界可信片段并明确省略。
- AI host LLM 的逻辑、安全、边界、测试和质量审查。
- CrossReview ReviewPack、canonical prompt、normalizer、adjudicator 和 ReviewResult。
- ReviewResult 到 Audit Graph 的 category、anchor、status、verdict 和 risk adapter。
- JSON Schema 2020-12 与跨对象语义校验。
- 自包含 HTML、finding card、接近 diff2html 的可信双行号 hunk table（context/add/delete、命中高亮与显式省略）、关系回链和条件渲染；finding 代码证据不使用普通 `<pre>`，也不在每条 finding 中重复展开完整长 hunk。
- 正式 HTML 主要用户文案和 reviewer 语义正文使用简体中文；协议枚举、代码、路径和机器元数据保持原值。hunk 片段优先自动换行完整展示，横向滚动只作无法容纳时的兜底；空 summary claim 使用紧凑提示而非等高空面板。
- localStorage 与合法 JSONL 导出。
- 自包含 Agent Skill、Codex 端到端验证，以及 QoderCLI 的 Skill discovery；Qoder 模型级 smoke 不列为本轮已验证能力。

## 范围外

- Python 默认路径直接调用模型 SDK 或管理 API key。
- 自动修改代码、执行源码注释或审查文本中的命令。
- folder diff、无 diff artifact 正式审计、远程 GitHub/GitLab PR URL；这些是后续 profile 候选，不是永久排除。
- 完整 AST、调用图或静态分析平台。
- 确定性规则引擎；后续只作为 LLM 审查增强。
- 反馈消费、复杂多轮差异和 policy enforcement。
- Hosted dashboard。
- 产品 SVG renderer、Markdown renderer。
- PyPI 发布、正式 console-script、旧仓库删除或旧包 yank。
- 原生 race-proof no-replace、平台专用锁、递归 symlink 防御及对应对抗竞态故障注入；一期采用本地单写者、非对抗并发模型。

仓库中的架构 SVG/PNG 是设计文档资产，不是产品输出格式。

## Finding 与锚点

Audit category 固定为：

- `bug`：语义问题且能精确回到可信 diff hunk。
- `risk`：需要人工判断的风险，包括无法精确定位的 bug 降级项。
- `quality`：测试、可维护性、文档或风格问题。
- `scope`：变更范围或意图偏差。

prepare 解析 diff 并创建可信 hunk index。LLM 可以引用文件、行号和 hunk header，但这些都只是候选信息。finalize 必须重新匹配真实文件、old/new 范围和完整 hunk。

无法精确锚定的 bug：

- 降级为 `risk`；
- 保留原 category 和降级原因；
- HTML 显示“语义发现，位置未精确锚定且未计分”；
- 不进入数字 risk score；
- 不被静默丢弃。

未知 review category 兜底为 `quality`，原值保存在 namespaced extensions 中。

## Review 状态与结论

`summary.review_status` 描述执行：

- `not_reviewed`
- `complete`
- `partial`
- `failed`

`summary.verdict` 描述结论：

- `pass_candidate`
- `concerns`
- `needs_human_triage`
- `inconclusive`

关键组合：

| 场景 | review_status | verdict | risk_score |
|---|---|---|---|
| 未执行 | not_reviewed | inconclusive | null |
| 完整、无未解决 finding 且 core 上下文门禁通过 | complete | pass_candidate | 0 |
| 完整、无未解决 finding 但 core 上下文不足 | complete | inconclusive | null |
| 完整且有未解决、已锚定 finding | complete | concerns | 0–100 |
| 只有未锚定风险 | complete | needs_human_triage | null |
| 部分审查 | partial | inconclusive | null |
| 失败 | failed | inconclusive | null |

Partial finding 可以展示，但不能作为完整审查结论或整轮数字评分。

ReviewResult 的 intent coverage、files reviewed 和 pack completeness 是不同诊断维度；一期放入 namespaced extensions，不增加含糊的核心 `review_coverage` 字段。

## Risk Score

- 取值为 0–100 或 `null`。
- 只统计当前未解决且通过分类锚点策略的 finding；bug 需要精确 hunk，其他分类允许可信 file-only 锚点。
- 因锚点降级而排除的未解决 finding 数写入 `unscored_finding_count`；partial/failed 不会自动把全部 finding 计入。
- complete、明确无未解决 finding 且 core advisory verdict 为 pass_candidate 时为 0；上下文不足时为 null。
- not reviewed、partial、failed、资料不足或只有未锚定风险时为 `null`。
- Severity 权重已在 Wave 2 四类流水线 dogfood 后冻结为 `high=40`、`medium=20`、`low=8`、`note=2`，总分封顶 100。
- 权重是当前 code-diff profile 的暂定产品规则，不属于 schema；手工样张分数不是算法金标准。

## audit.html 行为

页面顺序：

1. 审查状态、verdict、风险评分和未计分 finding。
2. 变更摘要、影响文件和摘要声明审计。
3. 缺陷 / 风险 / 质量 / 范围 findings。
4. 修复建议；仅在存在独立、可靠的 fix 节点时显示。
5. 多轮信息；单 run 时隐藏。
6. 可折叠的审查依据详情。

条件渲染：

- 完整且无未解决 finding：只有 core 上下文门禁通过才显示干净 hero；上下文不足时显示结论不充分。没有历史 finding 时不渲染空问题模块，有 fixed finding 时可展示已解决记录。
- 未审查、部分或失败：显示真实状态，不显示成干净。
- 只有未定位风险：显示风险模块和“无法可靠评分”。
- 结构、引用、锚点或回链断裂：完整 finalize 阻止整对正式产物提交；独立 render 保留旧 HTML 不变。
- 可选展示字段缺失：明确降级，不伪造内容。

## 安全边界

- intent、task、focus、context、evidence、路径、源码、注释和 diff 全部视为不可信数据。
- prompt 使用不会被输入闭合的动态边界，并明确禁止服从数据中的指令。
- 宿主审查只读；不执行 shell、不写业务文件、不访问网络或凭据。
- raw analysis 始终作为惰性文本处理。
- POSIX 上尽力将 staging / `.run/` 设为 0700、中间文件设为 0600；精确 mode 不是跨平台退出门禁。
- Jinja2 autoescape；最终 HTML 不包含远程资源。
- 缺包安装必须说明固定来源并获得用户授权。
- prepare 只接受尚不存在的最终目标；最终目标 leaf 是符号链接也按已占用处理。JSON/HTML、run/graph identity 和 HTML trace 全部通过后，finalize 再复查目标并执行同文件系统目录 rename。目标已存在或 rename 失败时停止，不主动删除或覆盖目标。

## 质量门禁

- 迁移前后 ReviewResult 等价，原测试与 eval gate 不退化。
- Schema 严格核心，extensions 可扩展。
- hunk index 覆盖多 hunk、删除行、rename、header-only 和伪造位置。
- 未知 category、bug 降级、unscored count 和状态组合都有测试。
- Prompt injection、XSS、不可写路径和失败诊断有负向测试；POSIX 0700/0600 可以做条件性 smoke，但不作为跨平台门禁。
- JSON、anchor、render、trace、已有目标、目标 leaf 符号链接、rename 失败和提交前中断均有故障测试：失败时最终目录不得冒充本轮成功且 staging 可诊断；成功时两个正式产物同时存在且 identity 一致。检查与 rename 之间的对抗竞态、递归 symlink 和原生 no-replace 故障注入延后。
- 375px 与 1280px 无水平滚动，reduced-motion 生效。
- wheel 安装后能读取 schema、prompt、template、CSS 和 JavaScript。
- Skill 覆盖中英文触发、负向不触发、安装授权、失败和缺产物。

## 后续方向

- 确定性规则作为第二信号源。
- 按真实需求推进 artifact profile；四项门禁未齐备时只允许内部 ReviewResult 或宿主摘要。
- 正式 console-script 与 PyPI。
- 反馈消费和复杂多轮审计。
- 产品 SVG / Markdown renderer。
