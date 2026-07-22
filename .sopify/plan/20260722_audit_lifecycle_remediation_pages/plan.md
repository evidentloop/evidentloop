---
title: EvidentLoop 审计闭环、修复验证与公开产品页
plan_id: 20260722_audit_lifecycle_remediation_pages
status: planned
lifecycle_state: planned
level: standard
created: 2026-07-22
updated: 2026-07-22
archive_ready: false
knowledge_sync:
  project: required
  background: review
  design: required
  tasks: required
---

# EvidentLoop 审计闭环、修复验证与公开产品页

就绪状态: Ready
依据: schema `0.5`、风险分删除、typed `fix_verification`、来源快照、claim 完成门、报告最终形态、Integration Gate、dogfood 前置门禁和 Wave 顺序均已收敛；外部发布仍是独立授权点。

## Context / Why

EvidentLoop 已能把本地 Git diff 生成可追溯的 `audit.json` / `audit.html`，并支持同一份代码上的人工裁定，但完整产品链仍有三个断点：

1. local-diff 正式入口没有把用户明确给出的审计重点传入已有 `ReviewPack.focus`。
2. `feedback_revision` 只能表达同一 `diff_version` 上的人工裁定；代码改变后，需要一个显式关联旧 finding、同时独立审查当前新 diff 的修复验证链路。
3. 当前报告仍围绕风险分和技术身份组织，移动端、裁定操作、修复验证与公开说明没有形成一条可理解的结果链。

系统不得从文件路径、提交信息、相似 diff、时间顺序或 finding 消失推断“代码因旧问题而修改”。唯一可信输入是用户或宿主显式选择旧 audit、具体 finding，并声明本次修复目标。

目标链路：

`显式 focus → 初次模型审查 → finding → 同 diff 人工裁定 → 代码修改 → 显式关联旧 finding → 新 diff 独立审查与修复验证 → 真实 dogfood 冻结 → Pages / README 公开证据`

## Scope

- 为 local-diff CLI、Python API 和官方 Skill 补齐显式 `focus`；不推断默认重点。
- 保持 `feedback_revision`：同一 `diff_version`、不重新审查代码、旧 audit 不可变、生成新 `report_version`。
- 新增 typed `fix_verification` 请求与 `extensions.evidentloop.fix_verification` 一跳来源契约；用户界面使用“修复验证 / Fix verification”，不再使用 `remediation` 作为新产品术语。
- 将公开 audit schema 升至 `0.5`，不读取、转换或兼容 schema `0.4`；旧报告不能进入新反馈或修复验证链路，只能重新生成。
- 从新链路彻底删除风险分：schema 字段、权重计算、delta、模型风险快照、renderer 展示、语义校验、测试和文档一起移除。
- 保留每个 finding 的严重度与人工 severity override；报告级使用 `overall_severity`，页面标签为“严重程度”。
- prompt 升至 `v0.6`，要求 reviewer 独立审查完整当前 diff，并分别判断每个修复声明。
- renderer 升至 `0.4`，按已确认样例完成结果优先、全宽 diff、裁定摘要、下方操作区、移动端与无障碍。
- 在 Pages 和 README 之前完成真实两轮 dogfood，冻结可信报告、事实和少量高价值截图。
- 双语 GitHub Pages 与 README 只使用冻结证据；只替换已经语义失真的素材。
- 候选版本目标为 package `0.1.0a3`、schema `0.5`、renderer `0.4`、prompt `v0.6`。

## Approach

### 1. 两类变更链路严格分开

- `feedback_revision`：来源与结果保持同一 `diff_version`；accept、false positive、comment、severity override 不调用 reviewer。
- `fix_verification`：当前 diff 必须与来源不同；用户显式选择旧 audit 和 finding；reviewer 审查完整新 diff，并额外验证声明。
- 混合 diff 合法，但修复关系只作用于明确选择的 finding，不能宣称整个 diff 都由旧 finding 导致。
- 新 CLI/API/Skill 使用 `fix_verification`；现有方案目录和分支名保留为历史追踪标识，不再扩散为公开契约。

### 2. Schema 0.5 是干净断点

- schema `0.5` 是唯一受支持的运行时 schema，不提供 `0.4 → 0.5` 迁移器、兼容 reader 或双写。
- 从 summary、revision snapshot 和相关验证中删除 `risk_score`、`risk_delta`、`model_risk_score`；删除 `SEVERITY_WEIGHTS` 和所有风险分文案、比较、样例与断言。
- 删除只为“是否计分”存在的 `unscored_finding_count`、`extensions.evidentloop.unscored` 和 `counted_in_risk`。保留 `risk` finding category、finding severity、`pack_completeness`、`downgraded_from` / `downgrade_reason` 与证据锚点事实；`needs_human_triage` 直接由锚点事实判定，不建立替代计分状态。
- `overall_severity` 是报告级 `high / medium / low / note / null`。完整审查时由当前有效 open findings 的严重度顺序确定；无 open finding 或审查不完整时为 `null`。UI 只写“严重程度”，不写“最高严重度”。
- 人工裁定后的 summary 保留 `model_verdict` 与 `model_overall_severity`，不新增 severity 分值或 delta；前后变化通过正式 run snapshot 展示。
- verdict 继续独立表达 `pass_candidate / concerns / needs_human_triage / inconclusive`，不能被 `overall_severity`、修复 claim 或人工评论替代。

### 3. 修复验证使用 typed 一跳契约

1. 请求必须携带用户看到的 expected `source_report_version`；实现读取来源 `audit.json` 原始字节、计算实际版本并先做相等校验，再校验 schema `0.5` 与语义。
2. 要求来源有非空 `diff_version`；finding id 与 fingerprint 必须同时匹配来源最新正式 run，且当前有效状态必须为 `open`。已 dismissed/fixed 的目标先在来源报告完成正式修订，不能直接进入修复验证。
3. 在任何输出目录或 staging 副作用前拒绝旧 schema、来源版本变化、相同 diff、非 open、未知、过期、冲突或重复目标。
4. 冻结当前新 diff 后，把 `claim_id`、最小来源摘要、冻结的 `source_title` 和用户声明加入 reviewer prompt。reviewer 必须输出单一 `Fix Verification Results` 块，每个输入 `claim_id` 恰好一项，包含 status、rationale 和证据引用。
5. parser 拒绝缺失、重复或未知 `claim_id`；completion gate 只有在 finding/overall assessment 与全部目标结果都完整时才为 complete，否则为 partial/failed。
6. `extensions.evidentloop.fix_verification` version `1` 只保存直接前驱 `report_version` / `diff_version`、逐目标 finding id/fingerprint、`source_title`、用户声明和 `claim_id`；不保存绝对路径、claim 状态、当前 verdict、当前严重程度或当前 `diff_version`。
7. 每个 claim 归属于当前 `model_review` run 的 `summary_audit.claims`。真值表固定为：`supported` 至少一条 support 且无 challenge；`challenged` 至少一条 challenge 且无 support；`partial` 两类 edge 都存在；`unknown` 两类 edge 都不存在且必须有明确 rationale。语义校验同时校验 claim status、edge 与 target 一一对应。
8. 当前 audit 的 `runs` 只包含当前 diff 的模型审查及后续同 diff 人工修订；旧 runs 不复制。

### 4. Audit report 按结果链收口

- 页头只展示审查状态、当前结论、报告级严重程度和旧问题验证结果；彻底移除风险分及旧/当前风险并排。
- 变更摘要是第一个业务区块，用户界面使用“问题”，技术身份 `finding-*` 下沉到需要核验的位置。
- 存在 `fix_verification` 时展示“上一轮问题是否已解决”：冻结的旧问题标题、用户声明、逐目标验证结果、关键证据和当前新审查结论彼此分开。单目标显示一个结果；多目标页头只显示 `supported / challenged / partial / unknown` 的分状态计数，不发明第五种聚合状态。
- finding 卡按已确认结构排列：为什么是问题 → 上方只读裁定摘要条 → 全宽单栏 unified diff → 下方全宽操作区。
- 裁定摘要显示模型判断、已应用的我的裁定和待提交变化；误报、severity override 与评论不覆盖 diff。
- 代码长行不折行；hunk 在有最大高度的容器内按需上下/左右滚动；文件头和节选说明在滚动区外。
- 原生 `<details>` 只向下扩展；不增加悬浮条、侧栏、全屏、搜索、复杂筛选、同步滚动、Diff2Html 或语法高亮依赖。
- 375px 下 truth grid 为 2×2，裁定摘要为 2+1，finding 标题全宽、状态徽标独立，裁定与导出按钮成对并排；页面本身无横向溢出。
- 无 `fix_verification`、finding、feedback history 或 fixes 时，对应 section 连标题一起省略。

### 5. Dogfood 先于宣传

- Wave 1–3 是不可单独交付的原子 P0 组。Integration Gate 通过后，再完成一个公开仓库的两轮真实审查：初次 finding、代码修改后的显式修复验证；另验证同 diff 人工裁定。
- dogfood 必须证明来源身份、schema `0.5`、claim、当前 verdict、overall severity、一跳 lineage、无绝对路径泄露和报告可操作性。
- 只有证据经用户审计并冻结后，才能据此写 Pages、README、双语说明和截图。
- 不重做全部历史宣传资产；只替换语义失真、重复或明显低质量的素材。

## Waves / Gates

- [x] Gate 0 · 决策冻结：schema `0.5` 不兼容 `0.4`、移除风险分、采用 `fix_verification`、冻结报告样例和非目标。
- [ ] Wave 1 · P0：schema/input/version 基础、风险分删除、focus、来源校验及本 Wave 测试。
- [ ] Wave 2 · P0：typed `fix_verification`、prompt/claim、provenance、CLI/API/Skill 实际流程及测试。
- [ ] Wave 3 · P0/P1：renderer/report、反馈历史、全宽 diff、移动端、fixture 与代表性视觉冒烟。
- [ ] Integration Gate · 可运行基线：核心全量 pytest、schema/package、doctor、Skill 与 artifact trace 通过，finalize/render/revise/fix verification 可共同运行。
- [ ] Gate A · 证据冻结：完成真实两轮 dogfood 和同 diff 人工裁定，用户审计后冻结可信资产。
- [ ] Wave 4 · P1：基于冻结资产完成 Pages、README、双语说明和必要截图。
- [ ] Wave 5 · P1：只做全量回归、构建、Skill、链接、视觉和站点闸门。
- [ ] Wave 6 · P2：候选版本独立审计；提交、推送、发布和 Pages 上线仍分别授权。

## Key Decisions

- 风险分没有足够用户解释力，且代码链路扩张成本高；schema `0.5` 直接删除，不做兼容层。
- 报告级“严重程度”和 finding 自身严重度是两个层次；前者使用 `overall_severity`，后者继续支持人工 override。
- 修复来源只接受用户确认版本中当前仍为 `open` 的 finding；`source_title` 是独立 HTML 所需的最小冻结快照，不授权回读或复制旧报告全文。
- 逐目标 claim 由当前 model review run 拥有；严格输出块、parser、completion gate 和 edge/status 真值表共同防止静默漏报。
- 修复验证跨 diff 证明是核心差异化能力；浏览器选择旧报告、自动匹配 finding、审计系列和中央 registry 继续是 v1 非目标。
- 旧风险与当前风险并排、风险箭头和风险宣传文案全部删除。
- 双语 Pages 有价值，但只能解释真实 dogfood 已证明的事实，不能先宣传后补证据。
- 组合为一个方案包、分 Wave 执行；Gate A 把证据生产与宣传实现隔开。
- 报告、Pages 与 README 共享事实和视觉语言，不共享运行时 CSS/JS；audit HTML 继续单文件自包含。
- 不引入前端框架、设计系统平台、图表、暗色主题、双栏 diff、搜索/复杂筛选、常驻侧边栏、全屏模式、远程字体、分析埋点或截图矩阵。

## Acceptance Criteria

- schema `0.5` 是源码、资源、doctor、Skill 与构建物中的唯一公开 schema；任何 `0.4` 输入在副作用前明确失败。
- `risk_score`、`risk_delta`、`model_risk_score`、风险权重和所有风险分 UI/测试从新链路消失；不得以另一种分值或等级表重建。
- `overall_severity`、verdict、review status 和 finding severity 的来源与语义可分别验证；人工裁定保留模型原值。
- focus 原样进入 ReviewPack；空白 focus 在读取 diff 或创建输出前失败。
- `fix_verification` 只有在 expected/actual `source_report_version`、schema、`diff_version`、finding id/fingerprint 与当前 `open` 状态全部匹配时接受；旧 audit 不变。
- 每个修复目标在当前 model review run 中恰好有一个 claim result；缺失、重复、未知目标或 edge/status 不一致会阻止 complete；finding 未重现不能单独证明修复。
- 独立 HTML 只依赖当前 audit 即可展示冻结的 `source_title` 和用户声明；多目标页头按四态计数，正文逐目标展示。
- 当前 runs 不拼接旧 diff；连续复审只引用直接前驱，不扫描目录、不建 registry、不自动匹配。
- 报告采用已确认的全宽单栏结构；长行和长 hunk 只在局部滚动，展开操作区不挤压 diff，关键控件至少 44×44。
- 375px 下页面无整体横向溢出，truth grid、裁定摘要、finding 标题、按钮和导出区保持已确认结构。
- Gate A 产出可核验、无敏感路径的真实报告；Pages、README 和截图只引用冻结事实。
- 全量 pytest、Ruff、schema/package resource、wheel/sdist、doctor、Skill、HTML trace、链接/metadata 与代表性视觉验收通过。

## Constraints / Not-in-scope

- 当前只更新并审计方案包，不修改业务代码、测试、长期知识、旧方案或线上站点。
- 方案目录与 feat 分支名保留历史标识；不因产品术语变化重命名 Git 分支或活动 plan id。
- 不回写既有 audit；schema `0.4` 报告保持原字节，只是不进入新链路。
- 不建立浏览器报告选择器、自动 finding matching、audit series、中央 registry、remediation backlog 或工单系统。
- 实施产物的 staging、commit、push、PR、release、PyPI 和 GitHub Pages 发布均需独立授权。

## Status / Progress

- [x] 当前 feat 分支已切换并保留用户既有改动。
- [x] 已完成代码与方案批判审计，确认风险分横跨 schema、summary、revision、validation、renderer 和测试。
- [x] 已完成可交互样例，并在桌面、展开态和 375px 下验证全宽 diff、局部双向滚动与移动端结构。
- [x] 已将用户最终裁定写回 `plan.md`、`tasks.md` 和样例审计说明。
- [x] 已完成独立 Agent 只读复审，并吸收 typed claim、来源快照/open 资格、unscored 删除和 Integration Gate 等最小修订。

## Next

停车等待用户确认是否按 Gate 0 → Wave 1–3 原子 P0 组开始实施；不自动修改业务代码或执行外部交付。
