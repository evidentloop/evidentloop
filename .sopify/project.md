# change-audit 项目约定

## 产品

`change-audit` 是面向 AI 变更与可审查产物的可回链审计工具。它把审查目标、宿主 LLM 的语义判断、可信锚点和用户决策整理为稳定产物；一期首个正式 profile 是本地 Git diff。

中文是主要产品文档与一期正式 HTML 报告语言。英文只保留在项目名、包元数据、命令、字段名、协议标签、代码和通用技术术语中；reviewer 输出的 finding、observation 与 overall 语义正文默认使用简体中文。

## 命名契约

- 产品、GitHub 仓库、未来 distribution 和 CLI：`change-audit`
- Python import package、源码目录：`change_audit`
- 内部隔离审查子系统：`change_audit.review`（能力源自 CrossReview）
- 内部数据模型：Audit Graph / `AuditGraph`
- 最终机器真相源：`audit.json`
- 默认人类界面：`audit.html`
- 用户反馈：`audit-feedback.jsonl`

CrossReview 是内部能力来源和迁移历史，不是一期第二个用户产品名。

## 产品分层

- `change_audit.review`：artifact-general 隔离审查内核，可按真实需求扩展 plan、design、analysis、review-result、agent output 等 ReviewPack/prompt/eval profile。
- `change_audit.audit` + renderer：正式审计产品层。artifact 类型只有具备 adapter、可信 anchor、eval baseline 和 renderer profile 后，才承诺 `audit.json` / `audit.html`。
- `code_diff`：一期首个正式 audit profile，不代表长期产品只支持 Git diff。

非 diff 类型在四项门禁前可以停在内部 ReviewResult 或宿主摘要，不能宣传为已经支持完整审计报告。

## 技术约定

- Python 版本：`>=3.10`。
- 结构契约：JSON Schema 2020-12 是唯一 schema 真相源；Python 只实现校验和语义约束，不建立第二套模型定义。
- 模板：Jinja2；CSS 和 JS 作为 package resources 维护并内联到自包含 HTML。
- 入口：一期保留 `python -m change_audit prepare/finalize/render`；正式 console-script 后续只做别名。
- 宿主边界：AI host LLM 负责语义审查，Python 基础安装不集成模型 SDK；可选 provider 只能进入 extra。
- Prompt provenance：prepare 冻结 product prompt source/version/hash，finalize 校验 prompt 文件及当前契约后再 ingest；跨进程版本漂移或 prompt 篡改不得冒充原版本完成。
- Reviewer payload：Git 文本 diff 不携带 `GIT binary patch`；binary 文件保留路径/change_type 元数据，视觉内容明确不在一期文本审查范围。
- 集成形态：一个 Python 包承载业务，一个用户级/宿主级 Skill 负责发现和编排，用户项目不复制集成文档。
- 一期默认输入：本地 Git diff；长期输入按 artifact profile 管理。
- 默认产物：`audit.json` 和 `audit.html`；`audit-feedback.jsonl` 由用户显式导出。
- 中间产物：prepare 在最终目录同父目录创建隐藏 staging workspace，`.run/` 位于其中；成功时目录整体提交，失败时 staging 留作诊断。
- 并发边界：一期按本地单写者、非对抗并发设计；提交前复查最终目标 leaf 不存在，再执行同文件系统目录 rename。目标已存在或 rename 失败时停止，不主动删除或覆盖目标。
- 隐私权限：POSIX 上尽力将 staging / `.run/` 设为 0700、中间文件设为 0600；精确 mode 不是跨平台退出门禁。

## 一期 code-diff 职责

- `prepare` 选择尚不存在的最终目录，在同父目录 staging 中生成可信 diff 上下文、hunk index 和隐藏审计骨架，并返回 `run_id`、final/staging 路径的结构化 locator。
- Skill 在隔离上下文中调用宿主 LLM，并写入原始审查输出。
- `finalize` ingest 审查结果、生成机械字段、仅在完整性门禁通过时复制转义后的 Overall Assessment 作为语义摘要、执行锚点/引用校验，在 staging 中生成并验证 JSON/HTML；提交前复查目标 leaf 不存在，再用同文件系统目录 rename 成对提交正式产物。目标已存在或 rename 失败时保留 staging 诊断并停止。
- `render` 只消费完整 `audit.json`，不读取 Git 或宿主状态；显式输出路径只授权原子替换该 HTML。
- code-diff 的 `audit.json` 保留完整可信 hunk；HTML finding 只显示命中附近的有界可信片段、真实双行号和明确省略标记。精确 diff range 属于 source 元数据，不作为报告主标题。
- HTML 对有界 hunk 片段优先自动换行并完整展示，横向滚动仅作极端内容兜底；没有 summary claim 时使用顶对齐紧凑提示，不占用与文件列表等高的空白区域。
- ReviewResult 没有独立修复建议时，adapter 不生成 fix；finding 的原因不能冒充修复动作。所有未计分 finding 都必须在 HTML 明示未精确定位。
- 完整 reviewer 输出仍可能因 pack completeness 不足而结论不充分；正式图保留 `complete + inconclusive + risk_score=null`，不得把零 finding 自动包装成候选通过。

## 状态约定

`review_status` 只描述审查过程，`verdict` 只描述结论。`partial` 和 `failed` 均为 `inconclusive` 且不输出数字风险分。覆盖率和解析诊断写入 `summary.extensions.change_audit.review_diagnostics`，不新增核心 `review_coverage`。

数字风险分只计算完成审查且锚点有效的 findings。无法锚定的语义 bug 降级为未计分 risk，保留原分类和原因；只有此类风险时 `risk_score = null` 并要求人工分诊。

## 当前边界

CrossReview `v0.1.0a4` 审查核心已经等价迁入 `change_audit.review`，原 337 项测试、固定 ReviewResult 和可重跑 eval 指标保持一致。JSON Schema、语义校验、纯消费 HTML renderer、Git diff adapter 和 `prepare -> host LLM -> finalize` 主链路已经落地；code-diff schema 经四类流水线 dogfood 冻结为 `0.2`，风险权重固定为 `40/20/8/2` 并封顶 100。HTML 用户决策与显式 JSONL 导出、自包含 AI host Skill 已落地；固定 Fireworks range 已从全新 staging 生成真实中文报告，7/7 finding 精确锚定 changed line，并通过同源基线对比、localhost 1280/375 DOM、429 项测试和 wheel 隔离安装。QoderCLI 已确认 Skill discovery，模型级 smoke 由用户后续手工完成。CrossReview 原仓库在用户再次授权前保持不变。

Fireworks 当前样张 HTML 另含一张按用户审计需要生成的内联技术架构 SVG；它是样张阅读附注，不属于 `audit.json`、renderer、schema 或正式产品链路，独立重渲染会恢复为无该附注的原始报告。

`audit.json 0.2` 冻结时只代表 code-diff audit profile；第二种真实 artifact profile 通过独立 ADR 和 schema 版本扩展，不在一期 schema 中预塞未验证字段。

一期不实现原生 race-proof no-replace、平台专用锁或递归 symlink 防御，也不承诺消除目标检查与 rename 之间的极小竞态；这些在真实多写者需求出现后单独加固。
