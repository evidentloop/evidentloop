# 任务清单: EvidentLoop 审计闭环、修复验证与公开产品页

目录: `.sopify/plan/20260722_audit_lifecycle_remediation_pages/`

## Gate 0 · 已冻结的产品与契约边界

- [x] 0.1 冻结 schema `0.5` 干净断点：不兼容 `0.4`，新链路彻底移除风险分。
  - 验收：方案明确删除 risk schema、计算、revision、validation、renderer、测试和文档链；不建立迁移器、双写或替代分数。
- [x] 0.2 冻结术语与核心对象：用户界面使用“修复验证 / Fix verification”，正式标识使用 `fix_verification`。
  - 验收：活动目录和分支名只作历史追踪；新 API、extension、Skill、文档和页面不继续扩散 `remediation`。
- [x] 0.3 冻结报告最终形态和非目标。
  - 验收：上方只读裁定摘要、全宽 diff、下方全宽操作区；无旧/当前风险并排、浏览器报告选择、自动 finding 匹配、series/registry 或第二套前端组件。
- [x] 0.4 冻结执行顺序：真实 dogfood 在 Pages 和 README 之前。
  - 验收：Gate A 未通过时不得制作最终宣传文案或截图。
- [x] 0.5 吸收独立代码审计的最小契约补全。
  - 验收：expected source version、`source_title`、仅 open 来源、逐目标 completion gate、unscored 删除、Integration Gate 和多目标分状态计数已写入单一方案。

## Wave 1 · P0 Schema、输入和版本边界

- [ ] 1.1 新建并接通公开 schema `0.5`，把源码常量、package resource、doctor、fixture 和版本错误统一到单一入口。
  - 验收：只接受 schema `0.5`；`0.4` 在读取反馈、冻结新 diff、创建输出目录或 staging 前失败；无兼容 reader、迁移器或双写。
- [ ] 1.2 从新链路完整删除风险分及其派生状态。
  - 验收：删除 `risk_score`、`risk_delta`、`model_risk_score`、`SEVERITY_WEIGHTS`、`unscored_finding_count`、`extensions.evidentloop.unscored`、score-only view/context、语义校验、文案和断言；不得换名重建分值。保留 `risk` category、finding severity、`pack_completeness`、downgrade provenance 与锚点事实。
- [ ] 1.3 引入报告级 `overall_severity`，保留 finding severity 和人工 override。
  - 验收：`overall_severity` 为 `high / medium / low / note / null`；无 open finding 或审查不完整时为 `null`；人工 summary 保留 `model_overall_severity`，不增加 severity delta。
- [ ] 1.4 为 `evidentloop prepare`、local-diff Python API 与官方 Skill 增加单个可选 `focus`。
  - 验收：缺省为 `None`；显式空白值在读取 Git diff、分配输出目录或 staging 前失败；不从路径、diff、历史报告或宿主状态推断。
- [ ] 1.5 定义 typed `fix_verification` 请求和严格的前置校验顺序。
  - 验收：请求携带 expected `source_report_version`；先读取来源原始字节并核对实际版本和 schema `0.5`，再确认非空 `diff_version`、匹配最新 run 的 finding id/fingerprint 与当前 `open` 状态，最后读取并冻结当前 diff；版本变化、相同 diff、非 open、未知/过期/冲突/重复目标无副作用失败。
- [ ] 1.6 完成本 Wave 定向测试。
  - 验收：覆盖 schema/version、风险字段不存在、overall severity、focus 三态、来源失败顺序与无输出/staging 副作用。

## Wave 2 · P0 Typed 修复验证链路

- [ ] 2.1 把已验证的来源 finding 摘要和用户声明作为受限上下文加入当前完整 diff 的 reviewer 输入，prompt 升至 `v0.6`。
  - 验收：reviewer 同时审查完整新 diff 与逐 finding 声明；输出单一 `Fix Verification Results` 块，每个输入 `claim_id` 恰好一项 status/rationale/evidence；路径相似、提交信息、时间顺序或 finding 未重现均不能单独证明修复。
- [ ] 2.2 输出逐目标修复 claim 与证据关系。
  - 验收：claim 归属于当前 `model_review` run；parser 拒绝缺失、重复或未知 `claim_id`，completion gate 因任何目标不完整而降级；`supported`=support only、`challenged`=challenge only、`partial`=两者都有、`unknown`=两者都无且有 rationale；当前 verdict 与 `overall_severity` 独立确定。
- [ ] 2.3 在 `extensions.evidentloop.fix_verification` 写入 version `1` 的最小一跳 provenance。
  - 验收：只含直接前驱 `report_version` / `diff_version`、finding id/fingerprint、冻结的 `source_title`、声明和 `claim_id`；serializer 与语义校验共用入口；不重复 claim 状态、当前 verdict、当前严重程度或当前 diff identity，不记录绝对路径。
- [ ] 2.4 保持 runs 与不可变性边界。
  - 验收：新 audit 只含当前 diff 的模型 run 与后续同 diff feedback runs；旧 runs 不复制，旧 audit 字节不变；连续验证只引用直接前驱，不扫描目录、不建 registry。
- [ ] 2.5 将 `feedback_revision` 适配 schema `0.5`。
  - 验收：同 diff、不调用 reviewer、null 反转、误报后 severity override 停用/恢复、model verdict/overall severity 保留和正式 run 顺序均有测试；没有风险 delta。
- [ ] 2.6 接通 CLI、Python API、官方 Skill 与公开说明的真实流程。
  - 验收：用户显式提供来源 audit、expected source report version、finding id/fingerprint、声明和当前新 diff；Skill 不只描述概念，能够产出并校验实际请求。
- [ ] 2.7 完成本 Wave 定向与连续复审测试。
  - 验收：覆盖混合 diff、四类 claim、未重现不等于修复、一跳 lineage、绝对路径泄露、同 diff 与跨 diff runs 不混写。

## Wave 3 · P0/P1 Audit report 整体收口

- [ ] 3.1 重建 renderer context 的单一结果模型，删除旧风险和死 context。
  - 验收：`report_truth` 只含 review status、verdict、overall severity、open count 与人工裁定 notice；使用 `fix_verification_view`；删除 `counted_in_risk`、风险 label/metric 和无模板消费者字段。
- [ ] 3.2 重排页头和变更摘要。
  - 验收：页头显示审查状态、当前结论、严重程度、旧问题验证；单目标显示结果，多目标按 `supported / challenged / partial / unknown` 分状态计数，不新增 aggregate status；变更摘要紧随其后；颜色由审查完整性与 verdict 决定，不由 finding severity 或修复 claim 决定。
- [ ] 3.3 实现已确认的 finding 纵向结构。
  - 验收：为什么是问题 → 只读裁定摘要 → 全宽单栏 unified diff → 下方全宽操作区；误报、severity override 和评论不覆盖 diff，用户界面使用“问题”而非裸露 `finding`。
- [ ] 3.4 收口 diff、反馈历史与动态模块。
  - 验收：完整 hunk 留在 JSON；renderer 单一可信节选保留全部关键行和明确省略计数；长行不折行，局部上下/左右滚动；只有存在数据时渲染 feedback history、fix verification、finding 和 fixes section。
- [ ] 3.5 完成原生交互、移动端和无障碍。
  - 验收：原生 details 只向下展开；状态 live region；关键控件至少 44×44；375px truth grid 2×2、裁定摘要 2+1、标题全宽、状态徽标独立、成对按钮并排，页面无整体横向溢出。
- [ ] 3.6 更新模板、CSS、原生 JS、fixture、trace 和 renderer 测试。
  - 实现参考：`assets/audit-report-concept.html` 与 `assets/audit-report-concept-review.md`；样例不是生产 fixture 或截图金丝雀。
  - 验收：普通模型报告、同 diff 多轮反馈、修复验证、无可选模块、100+ 行 hunk 和超长行均有最小代表性覆盖。
- [ ] 3.7 做桌面与 375px 代表性视觉冒烟。
  - 验收：展开操作区不改变 diff 宽度；滚动边界后仍能继续浏览报告；不建立截图矩阵。

## Integration Gate · Wave 1–3 可运行基线

- [ ] I.1 将 Wave 1–3 视为不可单独交付的原子 P0 组，并验证关键路径共同可运行。
  - 验收：finalize、render、feedback revise 与 fix verification 在 schema `0.5` 上同时工作，不存在删除风险字段后的中间断裂状态。
- [ ] I.2 在真实 dogfood 前运行核心集成门禁。
  - 验收：核心全量 pytest、schema/package resource、doctor、官方 Skill、artifact trace 与绝对路径检查通过；失败则回到对应 Wave，不进入 Gate A。

## Gate A · 真实证据冻结

- [ ] A.1 使用候选代码在一个公开仓库完成初次完整审查并冻结来源报告。
  - 验收：产生真实 finding，schema `0.5`、report/diff identity 与完整证据可核验，无本地敏感路径。
- [ ] A.2 用户显式选择来源 finding，对修改后的新 diff 完成独立修复验证。
  - 验收：expected/actual source version、当前 open 资格、冻结 source title、claim、当前 verdict、overall severity 与一跳 lineage 可核验；未重现不被当作唯一证据。
- [ ] A.3 对同一 diff 完成一次人工裁定并验证导出/更新链路。
  - 验收：不调用 reviewer，null 语义、模型原值、run 顺序和新 report version 正确。
- [ ] A.4 用户审计两轮报告并冻结可公开事实与少量高价值素材。
  - 验收：若 dogfood 结果与方案假设冲突，回到对应 Wave 修正；未冻结前不进入 Pages。

## Wave 4 · P1 Pages、README 与必要素材

- [ ] 4.1 核验实际 GitHub Pages source/config，再建立英文与简体中文等价静态页面。
  - 验收：不把 `/docs` 目录存在当作线上配置证据；不引入构建链、远程字体、跟踪脚本或动画库。
- [ ] 4.2 基于 Gate A 冻结事实完成价值、边界、审计闭环、真实报告、宿主集成、安装、FAQ 和 footer。
  - 验收：不要求读者先理解 Sopify；不宣传未被 dogfood 证明的能力；真实报告只有一个权威入口。
- [ ] 4.3 完成双语互链、SEO/社交元数据、复制回退、无障碍和响应式。
  - 验收：375/768/1024/1440 无页面横向溢出，触控区至少 44×44，链接与 no-JS 回退有效。
- [ ] 4.4 局部更新 README 与素材。
  - 验收：README 不复制 Pages；只替换语义失真、重复或明显低质量的 SVG/PNG/GIF，仍有效素材继续复用。
- [ ] 4.5 让 Pages、README 和文档引用同一冻结报告与权威安装入口。
  - 验收：不复制 audit runtime 资源，不保留互相冲突的截图或旧结论。

## Wave 5 · P1 全量回归与交付闸门

- [ ] 5.1 运行全量 pytest、Ruff、schema/package resource、wheel/sdist、doctor、Skill 分发与 HTML trace。
  - 验收：package `0.1.0a3`、schema `0.5`、renderer `0.4`、prompt `v0.6` 在源码、构建物、Skill 和 doctor 中一致。
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
