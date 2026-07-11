# change-audit 长期设计

## 架构边界

`change-audit` 对用户表现为一个产品、一个 Python 包和一个 AI host Skill。CrossReview 的可复用能力迁入 `change_audit.review`，不再作为外部运行时依赖或第二条用户链路。

长期模块边界：

- `change_audit.review`：artifact-general ReviewPack、审查 prompt、结果 ingest、ReviewResult、normalizer、adjudicator 和分类型 eval harness。
- `change_audit.audit`：profile-specific adapter、Audit Graph 组装、可信锚点校验和正式产物收口；一期先实现 Git diff。
- `change_audit.schemas` / `change_audit.validation`：唯一 JSON Schema 2020-12 契约和跨对象语义校验。
- `change_audit.renderers.html`：只消费完整 `audit.json`，输出自包含 `audit.html`。
- `integrations/agent-skill/change-audit`：负责发现用户意图、授权、宿主 LLM 调用和阶段编排，不复制 Python 业务逻辑。

基础安装不依赖模型 SDK。原 CrossReview provider-backed 模式如需保留，只能作为可选 extra 和迁移兼容能力，不能成为默认路径。

## Artifact profile 放行门禁

Review 内核可以先试验新的 artifact 类型；正式 audit 支持必须同时具备：

1. 将目标归一化为内部审查输入的 adapter。
2. 可验证 finding 归属的可信 anchor。
3. 能评估误报、漏报和完成度的 eval baseline。
4. 与目标结构匹配的 renderer profile。

四项未齐备时只允许内部 ReviewResult 或宿主摘要，不宣称已经支持 `audit.json` / `audit.html`。一期 `audit.json 0.2` 是 code-diff profile 契约，不是所有 artifact 的通用稳定 schema。

## 一期 code-diff profile 主链路

```text
用户自然语言请求
  -> AI host Skill
  -> prepare（同父目录隐藏 staging、Git diff、ReviewPack、可信 hunk index、审计骨架）
  -> host LLM 隔离语义审查
  -> finalize（ingest、adapter、锚点与引用校验、render、HTML 回链）
  -> staging 中的 audit.json + audit.html
  -> 提交前复查目标 leaf 不存在
  -> 同文件系统目录 rename
  -> 最终目录同时出现正式产物对
  -> 用户决策与可选 audit-feedback.jsonl
```

LLM 只提供需要语义理解的 finding 内容。Python 生成 node ID、edge、fingerprint、可信 hunk、summary、审查状态、结论和风险分数，避免要求 LLM 手工拼接完整 Audit Graph。

## 稳定入口

底层模块入口：

```bash
python -m change_audit prepare --diff HEAD~1 [--out DIR]
python -m change_audit finalize --out DIR [--keep-review-artifacts]
python -m change_audit render INPUT_JSON --out OUTPUT_HTML
```

- `prepare` 读取 Git diff，在尚不存在的最终目录旁创建隐藏 staging workspace 与运行上下文，并向 Skill 返回 `run_id`、`final_dir`、`staging_dir` 的结构化 locator；finalize 校验 locator 与 staging 运行身份一致。
- Skill 将隔离审查的原始输出写回运行上下文。
- `finalize` 在 staging 中完成 ingest、graph adapter、JSON/HTML 生成及全部校验；提交前复查最终目标 leaf 不存在，再用同文件系统目录 rename 成对提交正式产物。目标已存在或 rename 失败时停止并保留 staging 诊断。
- `render` 是纯消费入口；显式 `--out` 原子替换单个 HTML，失败时旧 HTML 与输入 JSON 均保持不变。

正式 `change-audit` console-script 可在接口稳定后作为别名加入；`python -m change_audit` 永久保留。Python 不公开一个假装能自行调用宿主 LLM 的 `review` 命令。

## 隐藏运行契约

`prepare` 在最终目录同父目录创建隐藏 sibling staging，例如 `audit/.<slug>.change-audit-staging/`；最终目录此时必须不存在。staging 内的 `.run/` 至少包含：

- `audit-skeleton.json`：run/change/file 等机械骨架；不是最终 `audit.json`。
- `review-pack.json`：隔离审查输入。
- `hunk-index.json`：可信 `hunk_id`、路径、old/new 行范围和完整 snippet。
- `prompt.md`：把系统审查指令与不可信源码/diff 明确分隔后的宿主输入。
- `raw-analysis.md`：宿主 LLM 原始输出。
- `review-result.json`：仅在诊断、失败或显式保留时物化。

成功提交前 `finalize` 默认清理 `.run/`；keep 模式则保留并随 staging 一起提交。对 prepare 已接受的新目标，提交前失败时最终目录保持不存在并保留 staging；提交检查时已有目标或目标 leaf 是符号链接则拒绝，rename 失败也不得冒充本轮成功。

一期采用本地单写者、非对抗并发模型，不承诺消除目标检查与 rename 之间的极小竞态。POSIX 上 0700/0600 是 best-effort 隐私设置，不是跨平台退出门禁；原生 race-proof no-replace、平台专用锁和递归 symlink 防御留待真实多写者需求出现后加固。

宿主拒绝或可归一化的审查失败可以从可信骨架生成 `review_status = failed` 的完整报告对；schema、安全、路径不可读写、render、trace 或目录提交等硬失败返回非零：新目标不创建最终目录，已有目标保持原样。两类失败都不得复用旧报告。

## 信任与安全边界

- 所有 artifact 内容、来源声明和文件名均视为不可信数据；code-diff profile 还包括源码、diff 和注释。Prompt 使用不可与载荷混淆的动态边界，并明确禁止执行载荷中的指令。
- Skill 不静默安装，不修改用户代码，不因报告生成而扩大授权范围。
- LLM 输出必须先 ingest，再经过 profile 对应的 JSON Schema、引用完整性和可信锚点校验。
- finding 的完整 hunk 由 Python 从可信 `hunk-index.json` 反查；不得信任 LLM 返回的 hunk header 或 snippet。exact anchor 只能落在真实新增行或删除行，context 行不能冒充原修改位置。
- 宿主输出只有具备完整结束标记且可解析时才可记为 `complete`；截断、拒绝和失败必须保留真实状态。

## 审查状态与结论

`summary.review_status` 描述过程状态：

- `not_reviewed`：尚未执行宿主审查。
- `complete`：审查流程完整结束。
- `partial`：审查截断或只覆盖部分输入。
- `failed`：审查或 ingest 失败。

`summary.verdict` 只描述审查结论：

- `pass_candidate`：仅在 `complete`、无未解决 findings 且 core advisory verdict 认为上下文充分时使用；可以保留 fixed 历史记录。完整输出但上下文不足时使用 `complete + inconclusive + risk_score=null`。
- `concerns`：仅在 `complete` 且存在未解决、可评分 findings 时使用。
- `needs_human_triage`：`complete` 且只有未锚定降级风险时使用。
- `inconclusive`：`not_reviewed`、`partial` 或 `failed`。

`partial` 即使保留了部分 findings，也必须是 `inconclusive` 且 `risk_score = null`。审查覆盖率、解析告警和文件统计不是核心字段，统一写入 `summary.extensions.change_audit.review_diagnostics`，避免产生第二套状态真相。

## finding 锚点与风险评分

可评分 finding 必须通过分类对应的可信锚点校验：bug 需要 `file_path + hunk_id + 行范围`，risk/quality/scope 允许可信 file-only 锚点。语义 bug 如果无法锚定，不静默丢弃，而是：

- 降级到 `risk`；
- 在 extensions 保留原 category 和降级原因；
- 严重度最高为 `medium`；
- HTML 标记“语义发现，位置未完全确认”。

风险评分是 `0–100` 的暂定指标，只计算审查完成、当前未解决且通过分类锚点策略的 findings。因锚点降级而排除的未解决 finding 单独计入 `unscored_finding_count`；如果只有未锚定风险，则 `risk_score = null`、`verdict = needs_human_triage`。权重在真实 dogfood 后冻结。

## 数据与渲染契约

对已经放行的 audit profile，`audit.json` 是唯一最终机器真相源。核心对象默认严格拒绝未知字段；扩展只允许放入 namespaced `extensions`。

Renderer 不读取 Git、ReviewPack、原始 LLM 输出或宿主状态。它依据完整 Audit Graph 输出单文件 HTML，并校验 `data-node-id`、`data-claim-id`、`data-fingerprint` 等回链。可选字段缺失时降级展示；结构或引用断裂时拒绝写出误导性报告。

Renderer 使用共同外壳展示 status、verdict、summary、findings、evidence、fix 和 human decision，定位模块按 profile 切换：code diff 在 `audit.json` 保留可信完整 hunk，HTML finding 只把命中附近的有界可信片段渲染成接近 diff2html 的双行号表格，区分 context/add/delete、突出 finding 命中行、明确标记省略并保留 `data-*` 回链；不得用通用 `<pre>` 承载 finding 代码证据。未来 plan/design 可使用 section、claim 和 excerpt。没有成熟 renderer profile 时不生成伪完整 HTML。

当前 `artifact` 节点表示由图谱派生的正式产物，不复用为被审查输入。第二种真实 profile 出现时，再通过独立 ADR 和 schema 版本引入 review target 与对应 anchor。

完整 review 的提交点是：全部校验通过后复查最终目标 leaf 不存在，再把同父目录 staging 通过一次同文件系统目录 rename 提交为最终目录。成功后最终目录同时含 `audit.json` 与 `audit.html`；检查时已有目标或 rename 失败则停止并保留 staging 诊断，不主动删除或覆盖目标。独立 `render --out` 只原子替换单个 HTML，不受产物对提交约束。

没有未解决 finding 且上下文充分时，`complete + pass_candidate` 表示完整审查未发现当前问题；上下文不足时保留 `complete + inconclusive`。没有历史 finding 时不渲染空列表，有 fixed finding 时可展示已解决记录；任何非 `pass_candidate` 状态都不能显示为通过。

## 用户反馈

`audit.html` 支持 finding 的 `accept`、`false_positive`、`comment` 和 `severity_override`，用 localStorage 暂存，并由用户显式导出 `audit-feedback.jsonl`。一期不自动读取反馈或修改代码。

## 宿主与发布

Skill 是发现和编排入口，不要求每个用户项目放置说明文件。Codex 已完成端到端 dogfood；QoderCLI 已确认 Skill discovery，模型级 smoke 按用户决定延后。其他能运行 shell 并提供 LLM 的宿主可按同一契约适配。

外部试用只引用真实固定 Git tag，不使用 `@latest`，不静默安装。CrossReview 原仓库在等价迁移、dogfood 和再次授权前保持可用，不删除、不提前归档。
