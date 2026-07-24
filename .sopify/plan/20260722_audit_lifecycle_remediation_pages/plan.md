---
title: EvidentLoop 审计闭环、修复验证与公开产品页
plan_id: 20260722_audit_lifecycle_remediation_pages
status: in_progress
lifecycle_state: in_progress
level: standard
created: 2026-07-22
updated: 2026-07-23
archive_ready: false
knowledge_sync:
  project: required
  background: review
  design: required
  tasks: required
---

# EvidentLoop 审计闭环、修复验证与公开产品页

就绪状态: Ready
依据: schema `0.5` 断点和风险分删除已经确认；typed `fix_verification`、`claim.reason`、来源快照、完成门、报告最终形态、Integration Gate、dogfood 前置门禁和 Wave 顺序均已收敛；外部发布仍是独立授权点。

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
- prompt 升至 `v0.7`，要求 reviewer 独立审查完整当前 diff、按实现逻辑生成最少必要的语义变更主题，并分别判断每个修复声明。
- renderer 升至 `0.4`，按已确认样例完成结果优先、全宽 diff、裁定摘要、下方操作区、移动端与无障碍。
- 在 Pages 和 README 之前冻结已完成 dogfood 的可信报告、事实和少量高价值截图；跨 diff 修复验证未完成真实 dogfood 时，只宣传能力，不宣传已通过真实验证。
- 双语 GitHub Pages 与 README 只使用冻结证据；只替换已经语义失真的素材。
- 候选版本目标为 package `0.1.0a3`、schema `0.5`、renderer `0.4`、prompt `v0.7`。

## Approach

### 1. 两类变更链路严格分开

- `feedback_revision`：来源与结果保持同一 `diff_version`；accept、false positive、comment、severity override 不调用 reviewer。
- `fix_verification`：当前 diff 必须与来源不同；用户显式选择旧 audit 和 finding；reviewer 审查完整新 diff，并额外验证声明。
- 混合 diff 合法，但修复关系只作用于明确选择的 finding，不能宣称整个 diff 都由旧 finding 导致。
- 新 CLI/API/Skill 使用 `fix_verification`；现有方案目录和分支名保留为历史追踪标识，不再扩散为公开契约。

### 2. Schema 0.5 是干净断点

- schema `0.5` 是唯一受支持的运行时 schema，不提供 `0.4 → 0.5` 迁移器、兼容 reader 或双写。
- 从 summary、revision snapshot 和相关验证中删除 `risk_score`、`risk_delta`、`model_risk_score`；删除 `SEVERITY_WEIGHTS` 和所有风险分文案、比较、样例与断言。
- 删除只为“是否计分”存在的 `unscored_finding_count`、`extensions.evidentloop.unscored` 和 `counted_in_risk`。保留 `risk` finding category、finding severity、`pack_completeness`、`downgraded_from` / `downgrade_reason` 与证据锚点事实。open finding 仅在 `downgraded_from == "bug"`，或缺少可信 `file_path` / `finding_in_file` 关联时需要人工分诊；保留既有 review/advisory 前置判断，其余完整审查中全部 open findings 都属于这两类时 verdict 为 `needs_human_triage`，只要存在其他 open finding 就为 `concerns`。该结果直接计算，不保存替代 `unscored` 字段。
- `overall_severity` 是报告级 `high / medium / low / note / null`。完整审查时由当前有效 open findings 的严重度顺序确定；无 open finding 或审查不完整时为 `null`。UI 只写“严重程度”，不写“最高严重度”。
- 人工裁定后的 summary 保留 `model_verdict` 与 `model_overall_severity`，不新增 severity 分值或 delta；前后变化通过正式 run snapshot 展示。
- verdict 继续独立表达 `pass_candidate / concerns / needs_human_triage / inconclusive`，不能被 `overall_severity`、修复 claim 或人工评论替代。

### 3. 修复验证使用 typed 一跳契约

1. 请求必须携带用户看到的 expected `source_report_version`；实现读取来源 `audit.json` 原始字节、计算实际版本并先做相等校验，再校验 schema `0.5` 与语义。
2. 要求来源有非空 `diff_version`；finding id 与 fingerprint 必须同时匹配当前已验证的来源报告，且该节点的当前有效状态必须为 `open`。finding 是报告当前状态，不归属于某个 run；人工 revision 通过事件重放更新它。已 dismissed/fixed 的目标先在来源报告完成正式修订，不能直接进入修复验证。
3. 在任何输出目录或 staging 副作用前拒绝旧 schema、来源版本变化、相同 diff、非 open、未知、过期、冲突或重复目标。
4. 冻结当前新 diff 后，把 `claim_id`、最小来源摘要、冻结的 `source_title` 和用户声明加入 reviewer prompt。reviewer 必须输出单一 `Fix Verification Results` 块，每个输入 `claim_id` 恰好一项，包含 status、reason 和证据引用。
5. parser 拒绝缺失、重复或未知 `claim_id`；completion gate 只有在 finding/overall assessment 与全部目标结果都完整时才为 complete，否则为 partial/failed。
6. `extensions.evidentloop.fix_verification` version `1` 只保存直接前驱 `report_version` / `diff_version`、逐目标 finding id/fingerprint、`source_title`、用户声明和 `claim_id`；不保存绝对路径、claim 状态、当前 verdict、当前严重程度或当前 `diff_version`。
7. 每个 claim 归属于当前 `model_review` run 的 `summary_audit.claims`，直接保存非空 `reason`，说明为什么得到该 status。真值表固定为：`supported` 至少一条 support 且无 challenge；`challenged` 至少一条 challenge 且无 support；`partial` 两类 edge 都存在；`unknown` 两类 edge 都不存在。schema `0.5` 的 `summary_audit.status` 支持这四态和 `not_audited`：无 claim 时为 `not_audited`，全部 claim 同态时取该状态，混合时为 `partial`；renderer 的多目标结果仍按四态计数，不展示这个技术汇总。语义校验同时校验 claim status、reason、edge 与 target 一一对应。
8. 当前 audit 的 `runs` 只包含当前 diff 的模型审查及后续同 diff 人工修订；旧 runs 不复制。

### 4. Audit report 按结果链收口

- 页头只展示审查状态、当前结论、报告级严重程度和旧问题验证结果；彻底移除风险分及旧/当前风险并排。
- 变更摘要是第一个业务区块：模型按实现逻辑选择最少必要的 1–5 个非重复主题，说明总体变化、行为变化、影响范围和审计重点，不按文件机械罗列；文件统计与完整文件列表继续作为辅助证据。复用现有 change 节点和 extensions，不升级 schema、不固定主题名称。用户界面使用“问题”，技术身份 `finding-*` 下沉到需要核验的位置。原始 claim 判断不因人工裁定被改写；关联问题全部离开 `open` 后，页面派生显示“模型曾判断什么”和“当前裁定是什么”，使用中性配色，并让文件问题入口同步表达待处理、已忽略或已修复。
- 页头说明不是固定模块：普通完整报告省略；人工裁定、部分完成、失败或未审查时才用一行直接文案解释特殊状态，不重复上方状态格。
- 存在 `fix_verification` 时展示“上一轮问题是否已解决”：冻结的旧问题标题、用户声明、逐目标验证结果、关键证据和当前新审查结论彼此分开。单目标显示一个结果；多目标页头只显示 `supported / challenged / partial / unknown` 的分状态计数，不发明第五种聚合状态。
- finding 卡按已确认结构排列：为什么是问题 → 有数据时就近显示“建议怎么改” → 上方只读裁定摘要条 → 全宽单栏 unified diff → 下方全宽操作区；不另建重复的修复建议区块，也不展示宽泛 category 徽标。
- 裁定摘要显示模型判断、已应用的我的裁定和待提交变化；误报、severity override 与评论不覆盖 diff。已忽略问题保留完整内容，但边线、严重度徽标和建议区使用中性配色，不再呈现为当前活跃风险。
- 代码长行不折行；hunk 在有最大高度的容器内按需上下/左右滚动；文件头和节选说明在滚动区外。
- 原生 `<details>` 只向下扩展；不增加悬浮条、侧栏、全屏、搜索、复杂筛选、同步滚动、Diff2Html 或语法高亮依赖。
- 375px 下 truth grid 为 2×2，裁定摘要为 2+1，finding 标题全宽、状态徽标独立，裁定与导出按钮成对并排；页面本身无横向溢出。
- 无 `fix_verification`、finding 或 feedback history 时，对应 section 连标题一起省略；没有关联 fix 时，问题卡不显示“建议怎么改”。

### 5. Dogfood 先于宣传

- Wave 1–3 是不可单独交付的原子 P0 组。Integration Gate 后已完成公开仓库的初次审查与同 diff 人工裁定；本轮按用户决定跳过跨 diff 修复验证报告。
- 已完成 dogfood 必须证明来源身份、schema `0.5`、当前 verdict、overall severity、无绝对路径泄露和报告可操作性。claim 与一跳 lineage 只有生成下一轮跨 diff 报告后才算真实 dogfood 证据。
- 只有证据经用户审计并冻结后，才能据此写 Pages、README、双语说明和截图。
- 不重做全部历史宣传资产；只替换语义失真、重复或明显低质量的素材。

## Waves / Gates

- [x] Gate 0 · 决策冻结：schema `0.5` 不兼容 `0.4`、移除风险分、采用 `fix_verification`、冻结报告样例和非目标。
- [x] Wave 1 · P0：schema/input/version 基础、风险分删除、focus、来源校验及本 Wave 测试。
- [x] Wave 2 · P0：typed `fix_verification`、prompt/claim、provenance、CLI/API/Skill 实际流程及测试。
- [x] Wave 3 · P0/P1：renderer/report、反馈历史、全宽 diff、移动端、fixture 与代表性视觉冒烟。
- [x] Integration Gate · 可运行基线：核心全量 pytest、schema/package、doctor、Skill 与 artifact trace 通过，finalize/render/revise/fix verification 可共同运行。
- [x] Gate A · 证据冻结：审计初次报告与同 diff 人工裁定，并按已确认边界冻结可信资产。
- [x] Wave 4 · P1：基于冻结资产完成 Pages、README、双语说明和必要截图。
- [ ] Wave 5 · P1：只做全量回归、构建、Skill、链接、视觉和站点闸门。
- [ ] Wave 6 · P2：候选版本独立审计；提交、推送、发布和 Pages 上线仍分别授权。

## Key Decisions

- 风险分没有足够用户解释力，且代码链路扩张成本高；schema `0.5` 直接删除，不做兼容层。
- 报告级“严重程度”和 finding 自身严重度是两个层次；前者使用 `overall_severity`，后者继续支持人工 override。
- 修复来源只接受用户确认版本中当前仍为 `open` 的 finding；`source_title` 是独立 HTML 所需的最小冻结快照，不授权回读或复制旧报告全文。
- 逐目标 claim 由当前 model review run 拥有；严格输出块、parser、completion gate 和 edge/status 真值表共同防止静默漏报。
- 修复验证跨 diff 证明是核心差异化能力；浏览器选择旧报告、自动匹配 finding、审计系列和中央 registry 继续是 v1 非目标。
- 反馈 JSONL 只更新同 diff 报告；只有用户另外明确要求修复代码时，宿主才按“修订报告 → 澄清与修复 → 定向测试 → 新 diff 下一轮报告”顺序编排。旧报告不覆盖、不删除，该顺序不引入新 schema、队列或状态机。
- 旧风险与当前风险并排、风险箭头和风险宣传文案全部删除。
- 双语 Pages 有价值，但只能解释真实 dogfood 已证明的事实，不能先宣传后补证据。
- 组合为一个方案包、分 Wave 执行；Gate A 把证据生产与宣传实现隔开。
- 报告、Pages 与 README 共享事实和视觉语言，不共享运行时 CSS/JS；audit HTML 继续单文件自包含。
- 不引入前端框架、设计系统平台、图表、暗色主题、双栏 diff、搜索/复杂筛选、常驻侧边栏、全屏模式、远程字体、分析埋点或截图矩阵。

## Acceptance Criteria

- schema `0.5` 是源码、资源、doctor、Skill 与构建物中的唯一公开 schema；任何 `0.4` 输入在副作用前明确失败。
- `risk_score`、`risk_delta`、`model_risk_score`、风险权重和所有风险分 UI/测试从新链路消失；不得以另一种分值或等级表重建。`needs_human_triage` 只按已有降级与可信文件关联事实确定。
- `overall_severity`、verdict、review status 和 finding severity 的来源与语义可分别验证；人工裁定保留模型原值。
- focus 原样进入 ReviewPack；空白 focus 在读取 diff 或创建输出前失败。
- `fix_verification` 只有在 expected/actual `source_report_version`、schema、`diff_version`、finding id/fingerprint 与当前 `open` 状态全部匹配时接受；旧 audit 不变。
- 每个修复目标在当前 model review run 中恰好有一个含非空 `reason` 的 claim result；缺失、重复、未知目标或 reason/edge/status 不一致会阻止 complete；`summary_audit.status` 按无 claim、同态、混合三种情况确定；finding 未重现不能单独证明修复。
- 独立 HTML 只依赖当前 audit 即可展示冻结的 `source_title` 和用户声明；多目标页头按四态计数，正文逐目标展示。
- 当前 runs 不拼接旧 diff；连续复审只引用直接前驱，不扫描目录、不建 registry、不自动匹配。
- 报告采用已确认的全宽单栏结构；长行和长 hunk 只在局部滚动，展开操作区不挤压 diff，关键控件至少 44×44。
- 375px 下页面无整体横向溢出，truth grid、裁定摘要、finding 标题、按钮和导出区保持已确认结构。
- Gate A 产出可核验、无敏感路径的真实报告；Pages、README 和截图只引用冻结事实。
- 全量 pytest、Ruff、schema/package resource、wheel/sdist、doctor、Skill、HTML trace、链接/metadata 与代表性视觉验收通过。

## Constraints / Not-in-scope

- 当前收口 Wave 1–3 的本地实现、测试、技术文档和方案状态；不修改旧方案或线上站点。
- 方案目录与 feat 分支名保留历史标识；不因产品术语变化重命名 Git 分支或活动 plan id。
- 不回写既有 audit；schema `0.4` 报告保持原字节，只是不进入新链路。
- 不建立浏览器报告选择器、自动 finding matching、audit series、中央 registry、remediation backlog 或工单系统。
- 实施产物的 staging、commit、push、PR、release、PyPI 和 GitHub Pages 发布均需独立授权。

## Status / Progress

- [x] 当前 feat 分支已切换并保留用户既有改动。
- [x] 已完成代码与方案批判审计，确认风险分横跨 schema、summary、revision、validation、renderer 和测试。
- [x] 已完成可交互样例，并在桌面、展开态和 375px 下验证全宽 diff、局部双向滚动与移动端结构。
- [x] 已将用户最终裁定写回 `plan.md`、`tasks.md` 和样例审计说明。
- [x] 已完成独立只读复审，并吸收 typed claim、来源快照/open 资格、风险分删除和 Integration Gate 等最小修订。
- [x] 用户已确认 schema `0.5` 断代且不保留 `0.4` 兼容层；claim 判断原因统一使用 `claim.reason`。
- [x] Wave 1 已收口：schema/input/version、风险分删除、overall severity、focus、来源前置校验与 canonical 技术文档一致；97 个定向测试、Ruff 和 diff 检查通过。
- [x] Wave 2 已收口：prompt/claim、严格一跳 provenance、反馈 revision、CLI/API/Skill 和技术说明形成真实链路；81 个定向测试、Ruff 和 diff 检查通过。
- [x] Wave 3 已收口：生产 renderer 按结果链局部重写，删除旧重复/空占位，完成动态语义变更摘要、条件状态说明、全宽单栏 diff、当前 diff 反馈历史、原生裁定交互、移动端与代表性视觉冒烟；用户复审后补齐短 diff 条件横滑、标准展开箭头、反馈表单响应式布局、可读的问题标题/动作/报告变化历史和纵向滚动链，将修复建议收回对应问题卡，移除用户含义不清的宽泛 category 徽标，让已忽略问题使用中性状态配色，并让变更摘要同步表达当前裁定。
- [x] Integration Gate 已通过：当前 package `0.1.0a3`、schema `0.5`、renderer `0.4`、prompt `v0.7` 已通过 414 个全量测试、Ruff、doctor、schema/package resources、Skill、artifact trace 与身份边界检查；最终收口补齐完整审查下 `inconclusive` 的严重程度、claim 汇总状态和跨 diff 身份校验，构建物和临时候选安装留在 Wave 5，不在本轮重复执行。
- [x] Gate A.1 已完成：当前完整实现 diff 的独立审查覆盖 41/41 个文件，正式报告为 `complete / concerns / medium`，包含 5 个 open findings；schema、report/diff identity、HTML trace 和绝对路径检查均通过。
- [-] Gate A.2 按用户决定跳过：不生成新的修复验证报告，不把来源报告改写为已修复，也不宣称跨 diff 验证已经完成。
- [x] Gate A.3 已完成：同一 diff 的人工认可与评论形成独立 `feedback_revision` run，保留模型原值和 `finding-004` 的 open 状态，新 report version 为 `sha256:c16b8641f24723b1fc44519ed875a3c139daf38512586d0d64d18a337f2bfb4c`。
- [x] Wave 1–3 检查点已提交并推送至当前 feat 分支，提交为 `9d22a510bc5be2952435b50c27b5b2f3bcdf99b7`；未创建 PR、发布或部署。
- [x] Gate A.4 已完成：首次 v0.7 dogfood 审出语义变更摘要未进入完成门，已回到 Wave 3 最小修复并提交为 `1af67963a5ff4c6ab5da10556d206901aa173601`；随后使用用户明确 focus 生成唯一权威的 `docs/examples/evidentloop-dogfood-v05/audit.json + audit.html`，结果为 `complete / pass_candidate / overall_severity=null`、43/43 个文件、0 findings，身份、trace、敏感路径与 1440/375 视觉检查通过。旧 concept HTML 已删除。
- [x] Wave 4 已完成：已核验 GitHub Pages 由 `main:/docs` 构建；英文与简体中文静态页、精简 README、代表性交互动画、双语生命周期图和手绘封面已统一到同一冻结证据。页面不含脚本、远程字体或分析埋点，桌面与 375px 无整体横向溢出；跨 diff 能力仍明确标注为尚无真实双 diff dogfood 证据。

## Next

Wave 4 已按用户确认范围收口；下一步进入 Wave 5，只运行一次全量回归、构建、Skill、链接和站点闸门。PR、发布、PyPI 与 Pages 上线仍需分别授权。
