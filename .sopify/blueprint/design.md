# EvidentLoop 长期设计

## 架构边界

`EvidentLoop` 是一个以 Python CLI 为产品面的开源审计工具。PyPI 包承载唯一确定性 runtime 与产品版本；同仓库标准薄 Skill 负责 AI host 发现和阶段编排；GitHub Pages 提供零安装预览。三者是同一产品的交付面，不扩张为平台。

跨 artifact profile 的稳定路径分为两层：各 profile 先把异构审查目标及其上下文、证据归一化为 artifact-general 审查契约（当前为 `ReviewPack` / `ReviewResult`），复用语义审查内核；再按 profile 完成可信锚定、验证、正式结论、适用时的评分和确定性呈现。当前类名和字段可以随真实 profile 演进，不把 code-diff 形态冻结为所有产物的永久输入结构。

审查目标、上下文和证据是一次审计中的角色，不是文件类型的固定属性。同一种结构化产物可以在不同审计目的下承担不同角色；只有审查目标需要由对应 profile 满足正式 audit 放行门禁。

长期模块边界：

- `evidentloop.review`：artifact-general ReviewPack、审查 prompt、结果 ingest、ReviewResult、normalizer 和 adjudicator；离线 eval 位于仓库 `prompt-lab/`，不进入正式 wheel。
- `evidentloop.audit`：profile-specific adapter、Audit Graph 组装、可信锚点校验和正式产物收口；一期先实现 Git diff。
- `evidentloop.schemas` / `evidentloop.validation`：唯一 JSON Schema 2020-12 契约和跨对象语义校验。
- `evidentloop.renderers.html`：只消费完整 `audit.json`，输出自包含 `audit.html`。
- Python CLI：通过 console script 提供 doctor、demo、prepare、finalize 和 render；uv/pipx 负责隔离安装、升级与卸载。
- `skills/evidentloop`：静态薄 Skill，负责发现用户意图、授权、宿主 LLM 调用和阶段编排；主 `SKILL.md` 保持宿主无关，已验证的宿主专属步骤放在一层 `references/` 中按需加载，不复制确定性业务逻辑，也不动态下载 prompt 或脚本。

确定性 runtime 不包含模型 SDK、provider/API key 配置或 standalone reviewer；AI host 是真实审查的主要模型执行面。Skill 只保留必要编排说明和展示元数据；`references/` 只承载按需加载的宿主验证 profile，不放审计内核、宿主 adapter 或模型调用脚本。

## Artifact profile 放行门禁

Review 内核可以先试验新的 artifact 类型；正式 audit 支持必须同时具备：

1. 将目标归一化为内部审查输入的 adapter。
2. 可验证 finding 归属的可信 anchor。
3. 能评估误报、漏报和完成度的 eval baseline。
4. 与目标结构匹配的 renderer profile。

四项未齐备时只允许内部 ReviewResult 或宿主摘要，不宣称已经支持 `audit.json` / `audit.html`。一期 `audit.json 0.3` 是 code-diff profile 契约，不是所有 artifact 的通用稳定 schema。

## 一期 code-diff profile 主链路

```text
用户自然语言请求
  -> AI host Skill
  -> runtime prepare（同父目录隐藏 staging、Git diff、ReviewPack、可信 hunk index、审计骨架）
  -> host LLM 语义审查（可用时隔离）
  -> runtime finalize（ingest、adapter、锚点与引用校验、render、HTML 回链）
  -> staging 中的 audit.json + audit.html
  -> 提交前复查目标 leaf 不存在
  -> 同文件系统目录 rename
  -> 最终目录同时出现正式产物对
  -> 用户决策与可选 audit-feedback.jsonl
```

LLM 只提供需要语义理解的 finding 内容。确定性 runtime 生成 node ID、edge、fingerprint、可信 hunk、summary、审查状态、结论和风险分数，避免要求 LLM 手工拼接完整 Audit Graph。

## 稳定入口

零安装预览与临时试用：

```bash
# 浏览 GitHub Pages 上的真实报告
uvx evidentloop demo
```

正式安装：

```bash
uv tool install evidentloop
npx skills add evidentloop/evidentloop --skill evidentloop -g
```

pipx 是 Python CLI 的 fallback。`demo` 使用 wheel 内独立合成 fixture，在临时 Git 仓库中复用现有主链并生成明确标记的完整演示报告；package 获取完成后，demo 本身不访问网络、不依赖当前目录，也不复用 dogfood 证据。`doctor` 检查 CLI/runtime/resources/Git，把 `npx` 缺失作为非阻断提示，并输出标准 Skill 安装命令、完整目录手工安装 fallback 和下一句可复制指令；它不扫描所有宿主目录，也不替安装器宣称 Skill 已被发现。

Skill 安装异常时使用标准 skills CLI 的 `list -g --json` 与宿主自身文档诊断。runtime 不维护宿主私有目录表；真实 discovery 只能由宿主内触发和发布 smoke 证明。

稳定 runtime 入口：

```bash
evidentloop prepare --diff HEAD~1 [--out DIR]
evidentloop finalize --out DIR [--keep-review-artifacts]
evidentloop render INPUT_JSON --out OUTPUT_HTML
```

- `prepare` 读取 Git diff，在尚不存在的最终目录旁创建隐藏 staging workspace 与运行上下文，并向 Skill 返回 `run_id`、`final_dir`、`staging_dir` 的结构化 locator；finalize 校验 locator 与 staging 运行身份一致。
- Skill 将宿主模型的原始输出写回运行上下文。
- `finalize` 在 staging 中完成 ingest、graph adapter、JSON/HTML 生成及全部校验；提交前复查最终目标 leaf 不存在，再用同文件系统目录 rename 成对提交正式产物。目标已存在或 rename 失败时停止并保留 staging 诊断。
- `render` 是纯消费入口；显式 `--out` 原子替换单个 HTML，失败时旧 HTML 与输入 JSON 均保持不变。

保留 `python -m evidentloop` 作为开发和诊断入口；普通用户文档不以它作为 Quick Start。runtime 不公开一个假装能自行调用宿主 LLM 的 `review` 命令。没有兼容 AI host 时，高级集成文档可以说明 `prepare -> external review -> finalize` 人工通道，但不提供本地 LLM/provider 集成，也不把它列入 README 首屏。

## 隐藏运行契约

`prepare` 在最终目录同父目录创建隐藏 sibling staging，例如 `audit/.<slug>.evidentloop-staging/`；最终目录此时必须不存在。staging 内的 `.run/` 至少包含：

- `audit-skeleton.json`：run/change/file 等机械骨架；不是最终 `audit.json`。
- `review-pack.json`：宿主审查输入。
- `hunk-index.json`：可信 `hunk_id`、路径、old/new 行范围和完整 snippet。
- `prompt.md`：把系统审查指令与不可信源码/diff 明确分隔后的宿主输入。
- `raw-analysis.md`：宿主 LLM 原始输出。
- `review-result.json`：仅在诊断、失败或显式保留时物化。

成功提交前 `finalize` 默认清理 `.run/`；keep 模式则保留并随 staging 一起提交。对 prepare 已接受的新目标，提交前失败时最终目录保持不存在并保留 staging；提交检查时已有目标或目标 leaf 是符号链接则拒绝，rename 失败也不得冒充本轮成功。

一期采用本地单写者、非对抗并发模型，不承诺消除目标检查与 rename 之间的极小竞态。POSIX 上 0700/0600 是 best-effort 隐私设置，不是跨平台退出门禁；原生 race-proof no-replace、平台专用锁和递归 symlink 防御留待真实多写者需求出现后加固。

宿主拒绝或可归一化的审查失败可以从可信骨架生成 `review_status = failed` 的完整报告对；schema、安全、路径不可读写、render、trace 或目录提交等硬失败返回非零：新目标不创建最终目录，已有目标保持原样。两类失败都不得复用旧报告。

## 信任与安全边界

- 所有 artifact 内容、来源声明和文件名均视为不可信数据；code-diff profile 还包括源码、diff 和注释。Prompt 以每次运行唯一的动态边界包裹 diff，文件列表中的换行与控制分隔符按单行数据转义，并明确禁止执行载荷中的指令；其余背景字段继续以“不可信声明”标签呈现，不宣称存在通用 prompt 注入隔离层。
- CLI 与 Skill 分别由用户显式调用 uv/pipx 和标准 skills CLI 安装；Skill 运行审计时不静默安装或升级，不修改用户代码，不因报告生成而扩大授权范围。
- LLM 输出必须先 ingest，再经过 profile 对应的 JSON Schema、引用完整性和可信锚点校验。
- finding 的完整 hunk 由确定性 runtime 从可信 `hunk-index.json` 反查；不得信任 LLM 返回的 hunk header 或 snippet。exact anchor 只能落在真实新增行或删除行，context 行不能冒充原修改位置。
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

`partial` 即使保留了部分 findings，也必须是 `inconclusive` 且 `risk_score = null`。审查覆盖率、解析告警和文件统计不是核心字段，统一写入 `summary.extensions.evidentloop.review_diagnostics`，避免产生第二套状态真相。

## finding 锚点与风险评分

可评分 finding 必须通过分类对应的可信锚点校验：bug 需要 `file_path + hunk_id + 行范围`，risk/quality/scope 允许可信 file-only 锚点。语义 bug 如果无法锚定，不静默丢弃，而是：

- 降级到 `risk`；
- 在 extensions 保留原 category 和降级原因；
- 严重度最高为 `medium`；
- HTML 标记“语义发现，位置未完全确认”。

风险评分是 `0–100` 的暂定指标，只计算审查完成、当前未解决且通过分类锚点策略的 findings。因锚点降级而排除的未解决 finding 单独计入 `unscored_finding_count`；如果只有未锚定风险，则 `risk_score = null`、`verdict = needs_human_triage`。权重在真实 dogfood 后冻结。

## 数据与渲染契约

对已经放行的 audit profile，`audit.json` 保存经过校验的结构化事实与结论，是后续验证、渲染和反馈重放的权威输入。核心对象默认严格拒绝未知字段；扩展只允许放入 namespaced `extensions`。

Renderer 不读取 Git、ReviewPack、原始 LLM 输出或宿主状态。它依据完整 Audit Graph 输出单文件 HTML，并校验 `data-node-id`、`data-claim-id`、`data-fingerprint` 等回链。可选字段缺失时降级展示；结构或引用断裂时拒绝写出误导性报告。

Renderer 使用共同外壳展示 status、verdict、summary、findings、evidence、fix 和 human decision，定位模块按 profile 切换：code diff 在 `audit.json` 保留可信完整 hunk，HTML finding 只把命中附近的有界可信片段渲染成接近 diff2html 的双行号表格，区分 context/add/delete、突出 finding 命中行、明确标记省略并保留 `data-*` 回链；不得用通用 `<pre>` 承载 finding 代码证据。未来 plan/design 可使用 section、claim 和 excerpt。没有成熟 renderer profile 时不生成伪完整 HTML。

当前 `artifact` 节点表示由图谱派生的正式产物，不复用为被审查输入。第二种真实 profile 出现时，再通过独立 ADR 和 schema 版本引入 review target 与对应 anchor。

完整 review 的提交点是：全部校验通过后复查最终目标 leaf 不存在，再把同父目录 staging 通过一次同文件系统目录 rename 提交为最终目录。成功后最终目录同时含 `audit.json` 与 `audit.html`；检查时已有目标或 rename 失败则停止并保留 staging 诊断，不主动删除或覆盖目标。独立 `render --out` 只原子替换单个 HTML，不受产物对提交约束。

没有未解决 finding 且上下文充分时，`complete + pass_candidate` 表示完整审查未发现当前问题；上下文不足时保留 `complete + inconclusive`。没有历史 finding 时不渲染空列表，有 fixed finding 时可展示已解决记录；任何非 `pass_candidate` 状态都不能显示为通过。

## 用户反馈

当前 `audit.html` 支持 finding 的 `accept`、`false_positive`、`comment` 和 `severity_override`，用 localStorage 暂存，并由用户显式导出 `audit-feedback.jsonl`。这是已经实现的反馈采集与导出能力，不冒充已经完成反馈消费。

反馈闭环是长期核心能力：runtime 在明确授权下消费结构化用户决策，重新裁决受影响的 finding，生成与来源 run 和所用反馈可回链的新审计版本，再从该结构化版本确定性渲染新的 `audit.html`。闭环不得直接修改 HTML 或原地覆盖来源 `audit.json`，避免 HTML 成为第二真相源，也保留“原始判断 -> 用户反馈 -> 修订结果”的完整链路。首个公开 Alpha 明确只记录并导出反馈；消费、重新裁决与报告重新生成按长期任务后续实施。

## 宿主与发布

PyPI package/CLI 是唯一 runtime 与产品版本真相源。静态 Skill 不维护独立语义版本，但必须声明兼容的 CLI/schema/prompt 范围，并在 `prepare` 前 fail closed；Skill 协议变化必须与对应 package release、不可变 Git tag 和安装 smoke 同步。

标准 Skill 目录是生态发现入口。发布检查使用 `skills@latest` 从仓库嵌套目录安装并核对辅助文件完整性；skills CLI 负责报告实际安装目标，`doctor` 不自研宿主 adapter 或通用发现扫描。产品不预设 Codex、Qoder 或其他宿主；支持表分别记录安装、Skill discovery、端到端审计与隔离增强的实测状态。

通用宿主主链为 `prepare -> host review -> finalize`。宿主把完整 prompt 交给模型，将一次完整原始响应写入运行上下文，并不因受审载荷中的指令执行命令、访问网络或凭据、修改业务文件。宿主能建立并确认独立 reviewer 上下文时使用隔离增强；thread ID、事件日志和临时目录只是宿主专属证据。隔离不进入 `audit.json`，也不改变 `review_status` 或 `verdict`。

发布前验证 clean wheel、console script、demo、doctor、package resources、Skill 嵌套安装和至少一个真实宿主端到端审计；随后创建与 package version 一致的不可变 Git tag，并通过 PyPI Trusted Publishing 发布。GitHub Release 页面可选；GitHub Pages 采用 `audit-evidence/docs`，无需额外前端框架或部署工作流。未经用户授权不创建 tag、Release 或 PyPI 发布。迁移来源仓库在再次授权前保持可用，不删除、不提前归档；EvidentLoop runtime 不读取它。
