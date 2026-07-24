# 任务清单: EvidentLoop 审计闭环、修复验证与公开产品页

目录: `.sopify/plan/20260722_audit_lifecycle_remediation_pages/`

## Gate 0 · 已冻结的产品与契约边界

- [x] 0.1 冻结 schema `0.5` 干净断点、风险分删除和“修复验证 / `fix_verification`”术语。
  - 验收：不兼容 `0.4`，不建立迁移器、双写、替代分数或第二套术语。
- [x] 0.2 冻结 typed 修复验证契约。
  - 验收：expected source version、`source_title`、仅 open 来源、`claim.reason`、逐目标完成门、一跳来源和多目标四态计数已写入单一方案。
- [x] 0.3 冻结报告形态、执行顺序和非目标。
  - 验收：只读裁定摘要、全宽 diff、下方操作区；真实 dogfood 在 Pages/README 之前；不增加浏览器报告选择、自动 finding 匹配、series/registry 或第二套前端组件。

## Wave 1 · P0 Schema、输入和版本边界

- [x] 1.1 新建并接通公开 schema `0.5`，把源码常量、package resource、doctor、fixture 和版本错误统一到单一入口。
  - 验收：只接受 schema `0.5`；`0.4` 在读取反馈、冻结新 diff、创建输出目录或 staging 前失败；无兼容 reader、迁移器或双写。
- [x] 1.2 从新链路完整删除风险分及其派生状态。
  - 验收：删除 `risk_score`、`risk_delta`、`model_risk_score`、`SEVERITY_WEIGHTS`、`unscored_finding_count`、`extensions.evidentloop.unscored`、score-only view/context、语义校验、文案和断言；不得换名重建分值。保留 `risk` category、finding severity、`pack_completeness`、downgrade provenance 与锚点事实；在既有 review/advisory 前置判断后，需人工分诊直接由“`downgraded_from == "bug"` 或缺少可信文件关联”判定，不保存替代字段。
- [x] 1.3 引入报告级 `overall_severity`，保留 finding severity 和人工 override。
  - 验收：`overall_severity` 为 `high / medium / low / note / null`；无 open finding 或审查不完整时为 `null`；人工 summary 保留 `model_overall_severity`，不增加 severity delta。
- [x] 1.4 为 `evidentloop prepare`、local-diff Python API 与官方 Skill 增加单个可选 `focus`。
  - 验收：缺省为 `None`；显式空白值在读取 Git diff、分配输出目录或 staging 前失败；不从路径、diff、历史报告或宿主状态推断。
- [x] 1.5 定义 typed `fix_verification` 请求和严格的前置校验顺序。
  - 验收：请求携带 expected `source_report_version`；先读取来源原始字节并核对实际版本和 schema `0.5`，再确认非空 `diff_version`、匹配当前已验证来源报告的 finding id/fingerprint 与当前 `open` 状态，最后读取并冻结当前 diff；finding 表示报告当前有效状态，不另造 run 归属；版本变化、相同 diff、非 open、未知/过期/冲突/重复目标无副作用失败。
- [x] 1.6 完成本 Wave 定向测试。
  - 验收：覆盖 schema/version、风险字段不存在、overall severity、focus 三态、来源失败顺序与无输出/staging 副作用。

## Wave 2 · P0 Typed 修复验证链路

- [x] 2.1 把语义变更摘要、已验证的来源 finding 摘要和用户声明加入当前完整 diff 的 reviewer 输入，prompt 升至 `v0.7`。
  - 验收：reviewer 按实现逻辑选择最少必要的 1–5 个变更主题，同时独立审查完整新 diff 与逐 finding 声明；输出单一 `Fix Verification Results` 块，每个输入 `claim_id` 恰好一项 status/reason/evidence；路径相似、提交信息、时间顺序或 finding 未重现均不能单独证明修复。
- [x] 2.2 输出逐目标修复 claim 与证据关系。
  - 验收：claim 归属于当前 `model_review` run，并直接保存非空 `reason`；parser 拒绝缺失、重复或未知 `claim_id`，completion gate 因任何目标不完整而降级；`supported`=support only、`challenged`=challenge only、`partial`=两者都有、`unknown`=两者都无；schema `0.5` 的 `summary_audit.status` 支持四态和 `not_audited`，无 claim 时为 `not_audited`，同态取该状态，混合为 `partial`；当前 verdict 与 `overall_severity` 独立确定。
- [x] 2.3 在 `extensions.evidentloop.fix_verification` 写入 version `1` 的最小一跳 provenance。
  - 验收：只含直接前驱 `report_version` / `diff_version`、finding id/fingerprint、冻结的 `source_title`、声明和 `claim_id`；serializer 与语义校验共用入口；不重复 claim 状态、当前 verdict、当前严重程度或当前 diff identity，不记录绝对路径。
- [x] 2.4 保持 runs 与不可变性边界。
  - 验收：新 audit 只含当前 diff 的模型 run 与后续同 diff feedback runs；旧 runs 不复制，旧 audit 字节不变；连续验证只引用直接前驱，不扫描目录、不建 registry。
- [x] 2.5 将 `feedback_revision` 适配 schema `0.5`。
  - 验收：同 diff、不调用 reviewer、null 反转、误报后 severity override 停用/恢复、model verdict/overall severity 保留和正式 run 顺序均有测试；没有风险 delta。
- [x] 2.6 接通 CLI、Python API、官方 Skill 与公开说明的真实流程。
  - 验收：用户显式提供来源 audit、expected source report version、finding id/fingerprint、声明和当前新 diff；Skill 不只描述概念，能够产出并校验实际请求。
- [x] 2.7 完成本 Wave 定向与连续复审测试。
  - 验收：覆盖混合 diff、四类 claim、未重现不等于修复、一跳 lineage、绝对路径泄露、同 diff 与跨 diff runs 不混写。

## Wave 3 · P0/P1 Audit report 整体收口

- [x] 3.1 重建 renderer context 的单一结果模型，删除旧风险和死 context。
  - 验收：`report_truth` 只含 review status、verdict、overall severity、open count 与人工裁定 notice；使用 `fix_verification_view`；删除 `counted_in_risk`、风险 label/metric 和无模板消费者字段。
- [x] 3.2 重排页头和变更摘要。
  - 验收：页头显示审查状态、当前结论、严重程度、旧问题验证；普通完整报告不显示额外说明，人工裁定或审查不完整时只显示一行说明。变更摘要使用动态逻辑主题、审计重点和辅助文件统计，完整文件列表不变；缺失或无效语义摘要降级为 `partial`，不得以原确定性摘要伪装完整输出。单目标显示结果，多目标按 `supported / challenged / partial / unknown` 分状态计数，不新增 aggregate status；原始 claim 不因人工裁定被改写，关联问题全部离开 `open` 后派生显示模型原判断与当前裁定，文件入口同步表达待处理、已忽略或已修复；颜色由审查完整性与 verdict 决定，不由 finding severity 或修复 claim 决定。
- [x] 3.3 实现已确认的 finding 纵向结构。
  - 验收：为什么是问题 → 有关联时就近显示“建议怎么改” → 只读裁定摘要 → 全宽单栏 unified diff → 下方全宽操作区；不另建重复修复建议区块，不展示宽泛 category 徽标，误报、severity override 和评论不覆盖 diff，已忽略问题保留完整内容但使用中性状态配色，用户界面使用“问题”而非裸露 `finding`。
- [x] 3.4 收口 diff、反馈历史与动态模块。
  - 验收：完整 hunk 留在 JSON；renderer 单一可信节选保留全部关键行和明确省略计数；长行不折行，局部上下/左右滚动；只有存在数据时渲染 feedback history、fix verification、finding 和 finding 内的 fix 建议。
- [x] 3.5 完成原生交互、移动端和无障碍。
  - 验收：原生 details 只向下展开；状态 live region；关键控件至少 44×44；375px truth grid 2×2、裁定摘要 2+1、标题全宽、状态徽标独立、成对按钮并排，页面无整体横向溢出。
- [x] 3.6 更新模板、CSS、原生 JS、fixture、trace 和 renderer 测试。
  - 实现记录：概念 HTML 已在 Gate A.4 删除；`assets/audit-report-concept-review.md` 只保留设计收口与权威证据指针，不再维护第二份样例。
  - 验收：普通模型报告、1/3/5 个动态变更主题、无效摘要回退、同 diff 多轮反馈、修复验证、无可选模块、100+ 行 hunk 和超长行均有最小代表性覆盖。
- [x] 3.7 做桌面与 375px 代表性视觉冒烟。
  - 验收：展开操作区不改变 diff 宽度；滚动边界后仍能继续浏览报告；不建立截图矩阵。

## Integration Gate · Wave 1–3 可运行基线

- [x] I.1 将 Wave 1–3 视为不可单独交付的原子 P0 组，并验证关键路径共同可运行。
  - 验收：finalize、render、feedback revise 与 fix verification 在 schema `0.5` 上同时工作，不存在删除风险字段后的中间断裂状态。
- [x] I.2 在真实 dogfood 前运行核心集成门禁。
  - 验收：核心全量 pytest、schema/package resource、doctor、官方 Skill、artifact trace 与绝对路径检查通过；失败则回到对应 Wave，不进入 Gate A。

## Gate A · 真实证据冻结

- [x] A.1 使用候选代码在一个公开仓库完成初次完整审查并冻结来源报告。
  - 验收：产生真实 finding，schema `0.5`、report/diff identity 与完整证据可核验，无本地敏感路径。
- [-] A.2 用户显式选择来源 finding，对修改后的新 diff 完成独立修复验证。
  - 验收：expected/actual source version、当前 open 资格、冻结 source title、claim、当前 verdict、overall severity 与一跳 lineage 可核验；未重现不被当作唯一证据。
  - 本轮决定：用户跳过生成新的修复验证报告；仅最小修复 `finding-004` 并运行定向测试，因此不形成 A.2 证据，也不宣称修复验证链路已经完成。
- [x] A.3 对同一 diff 完成一次人工裁定并验证导出/更新链路。
  - 验收：不调用 reviewer，null 语义、模型原值、run 顺序和新 report version 正确。
  - 结果：`finding-004` 的认可与评论已形成独立 `feedback_revision` run；来源 finding 保持 `open`，当时的报告明确标注人工裁定且未重新审查代码，新 report version 为 `sha256:c16b8641f24723b1fc44519ed875a3c139daf38512586d0d64d18a337f2bfb4c`。
- [x] A.4 用户审计初次报告与同 diff 人工裁定，冻结可公开事实与少量高价值素材。
  - 验收：明确记录“支持跨 diff 修复验证，但尚未通过真实跨 diff dogfood”；若现有证据与方案假设冲突，回到对应 Wave 修正；未冻结前不进入 Pages。
  - 结果：首次 v0.7 dogfood 发现语义变更摘要未进入完成门；已回到 Wave 3 最小修复并提交为 `1af67963a5ff4c6ab5da10556d206901aa173601`，没有增加 schema、模块或状态层。
  - 权威产物：`docs/examples/evidentloop-dogfood-v05/audit.json` 与 `audit.html` 使用固定范围 `555f84911e8892704f69d7faee4e06cf5a71ae7b..1af67963a5ff4c6ab5da10556d206901aa173601`、schema `0.5`、prompt `v0.7` 和用户明确 focus 生成；结果为 `complete / pass_candidate / overall_severity=null`，覆盖 43/43 个文件、0 findings。
  - 证据校验：diff version `sha256:055235edb0ef8f0c3f89a5e4c88aca5fd06e6e842483d48583b5f21508080f2d`，report version `sha256:38e425a6bd2f860f0b3f737ca030b2e05b5c00b03a4a4ab428c6fbfe0bfd18cf`；schema、run、HTML trace、敏感路径、1440 与 375 无横向溢出均通过。
  - 资产收口：旧 `assets/audit-report-concept.html` 已删除，审计说明缩减为权威证据指针；后续 Pages/README 只引用这一份真实报告。可以宣传“支持显式跨 diff 修复验证”，但不能宣传“已通过真实跨 diff dogfood”。

## Wave 4 · P1 Pages、README 与必要素材

### 已确认的产品叙事与页面线索

- 核心价值：EvidentLoop 不只是“生成一次代码审计报告”，而是把本地 Git diff、模型审查、人工裁定和下一轮修复验证连成可追溯的审计闭环。
- 两条链路必须分开说明：同 diff 反馈只修订报告、不修改或重新审查代码；用户明确要求修复代码时，才显式选择旧 finding、独立审查完整新 diff，并生成同一审计链路的下一轮报告，旧报告保持不可变，不从文件、提交或 finding 消失自动推断修复关系。
- 报告首屏分别表达审查是否完整、当前结论、报告级严重程度和旧问题验证，不能用其中一个替代另一个；阅读顺序固定为“报告结论 → 语义化变更摘要 → 修复验证（有数据时）→ 当前问题与裁定 → 反馈与复审历史（有数据时）→ 报告身份与校验信息”，无数据的模块整体省略。
- 变更摘要按实现逻辑由模型选择最少必要的 1–5 个主题，优先回答为什么改、核心行为变化、影响模块和风险关注点；文件数、增删行和完整文件列表只作辅助，不用文件罗列代替业务摘要。
- 报告体验亮点是结果优先、问题 `n/N`、待处理问题默认展开、已忽略或已修复问题默认收起、状态中性化、全宽单栏 diff、长行/长 hunk 局部滚动，以及桌面和移动端同一 DOM 的响应式阅读；不宣传成 IDE 或图表产品。
- 公开事实边界：可以宣传“支持显式跨 diff 修复验证”，但 A.2 已跳过，不能宣传“已通过真实跨 diff dogfood”；真实报告、截图、Pages 和 README 只引用 Gate A.4 冻结证据。
- 可选素材只在用户明确要求时由 Fireworks Tech Graph 生成变更架构 SVG；不默认生成、不绑定 EvidentLoop runtime，也不让图替代文字摘要。
- Pages 负责完整价值、证据和边界说明；README 只保留定位、快速开始、权威安装入口和真实报告入口，不复制整页内容。

- [x] 4.1 核验实际 GitHub Pages source/config，再建立英文与简体中文等价静态页面。
  - 验收：不把 `/docs` 目录存在当作线上配置证据；不引入构建链、远程字体、跟踪脚本或动画库。
  - 实现记录：GitHub API 确认 Pages 状态为 `built`、来源为 `main:/docs`；本 Wave 只准备源码，未触发部署。
- [x] 4.2 基于 Gate A 冻结事实完成价值、边界、审计闭环、真实报告、宿主集成、安装、FAQ 和 footer。
  - 验收：使用上述已确认叙事，不要求读者先理解 Sopify；不宣传未被 dogfood 证明的能力；真实报告只有一个权威入口。
- [x] 4.3 完成双语互链、SEO/社交元数据、复制回退、无障碍和响应式。
  - 验收：375/768/1024/1440 无页面横向溢出，触控区至少 44×44，链接与 no-JS 回退有效。
- [x] 4.4 局部更新 README 与素材。
  - 验收：README 不复制 Pages；只替换语义失真、重复或明显低质量的 SVG/PNG/GIF，仍有效素材继续复用；可选架构 SVG 遵守“用户明确要求才生成”的边界。
- [x] 4.5 让 Pages、README 和文档引用同一冻结报告与权威安装入口。
  - 验收：不复制 audit runtime 资源，不保留互相冲突的截图或旧结论。
  - 实现记录：交互 GIF 明确标注为代表性演示；43/43、0 findings 的 dogfood 报告保持唯一真实证据，未把 A.2 跳过的双 diff 验证宣传为已完成。

## Wave 5 · P1 全量回归与交付闸门

- [ ] 5.1 运行全量 pytest、Ruff、schema/package resource、wheel/sdist、doctor、Skill 分发与 HTML trace。
  - 验收：package `0.1.0a3`、schema `0.5`、renderer `0.4`、prompt `v0.7` 在源码、构建物、Skill 和 doctor 中一致。
- [ ] 5.2 运行反馈、修复验证、renderer、Pages、链接、metadata 和绝对路径泄露的完整门禁。
  - 验收：不存在 schema `0.4` 兼容分支、风险分残留、空模块、断链、错误语言互链或站点横向溢出。
- [ ] 5.3 做少量最终视觉验收。
  - 验收：桌面与 375px 覆盖普通报告、多轮反馈、修复验证和 Pages 英中页面；不增加快照矩阵。

## Wave 6 · P2 候选审计与外部授权

- [ ] 6.1 对候选版本做独立代码与 artifact 审计。
  - 验收：方案范围、版本、schema、Skill、包、报告、站点和 dogfood 证据一致；无高优先级未闭环问题。
- [ ] 6.2 候选审计通过后停车，等待用户分别授权 staging/commit、push/PR、release/PyPI 和 Pages 上线。
  - 验收：开发完成不自动触发任何外部动作；每类交付分别核验并留证。
- [ ] 6.3 按 `knowledge_sync` 更新长期约定；只有显式 `~go finalize` 才归档。
  - 验收：旧方案、用户工作区改动和历史 audit 均未被覆盖。
