# EvidentLoop 项目约定

## 命名契约

- 产品：`EvidentLoop`；GitHub 目标仓库：`evidentloop/evidentloop`；PyPI distribution 与 CLI：`evidentloop`
- Python import package、源码目录：`evidentloop`
- 内部语义审查子系统：`evidentloop.review`
- 内部数据模型：Audit Graph / `AuditGraph`
- 正式结构化审计记录：`audit.json`
- 默认阅读与反馈入口：`audit.html`
- 用户反馈：`audit-feedback.jsonl`

中文是主要产品文档与一期正式 HTML 报告语言。英文只保留在项目名、包元数据、命令、字段名、协议标签、代码和通用技术术语中；reviewer 输出的 finding、observation 与 overall 语义正文默认使用简体中文。

## 公开交付状态

- 首个公开 Alpha 为 `v0.1.0a0`，source commit 为 `88134ae4bba0fa9995a6bb2d46ba17f9e0bcc6b6`。
- PyPI 项目为 `evidentloop`；GitHub Release 为 `v0.1.0a0` pre-release；GitHub Pages 从 main 的 `/docs` 发布到 `https://evidentloop.github.io/evidentloop/`。
- Release evidence bundle 外层 SHA-256 为 `3be3ee211f6e8247a8586331860e1892ffcc823f002db2e6d0510053126bd57d`，manifest、tag 解引用与远端 main 均绑定同一 source commit。
- 后续发布继续遵守“准确 release commit 审计 → evidence → tag/Release → 受保护 PyPI deployment → 公开安装与 Pages smoke”的 fail-closed 顺序。

## 技术约定

- Python runtime 版本：`>=3.10`；推荐由 `uv tool` 管理隔离环境，pipx 作为 fallback，不要求用户手建 venv 或把包装进项目环境。
- 结构契约：JSON Schema 2020-12 是唯一 schema 真相源；当前候选 audit schema 为 `0.5`，canonical `$id` 为 `https://evidentloop.github.io/evidentloop/schemas/audit-v0.5.schema.json`。当前候选 runtime 只接受 `0.5`；`0.4` 及更早报告保持历史只读，必须重新生成后才能进入反馈或修复验证链路，不建立迁移器、兼容 reader 或双写。
- 模板：Jinja2；CSS 和 JS 作为 package resources 维护并内联到自包含 HTML。
- 入口：零安装预览使用 GitHub Pages，临时试用使用 `uvx evidentloop demo`，正式安装使用 `uv tool install evidentloop`（或 pipx）与标准 skills CLI；安装后由 AI host 自然语言触发。`evidentloop prepare/finalize/render/revise` 是稳定集成入口，`python -m evidentloop` 保留为开发与诊断入口。
- 宿主边界：产品 runtime 不执行模型；真实语义输出由外部 AI host/LLM 提供。Python 包不集成模型 SDK，也不读取 provider/API key 配置。
- 隔离边界：宿主能建立并确认独立 reviewer 上下文时将其作为增强；不具备时仍由当前宿主 LLM 执行同一主链。宿主专属 thread 或事件只作为增强证据。Python runtime 不证明隔离，正式产物不记录或暗示隔离等级。
- Prompt provenance：prepare 冻结 product prompt `source="product"`、version `v0.7` 与 hash，finalize 校验 prompt 文件及当前契约后再 ingest；跨进程版本漂移或 prompt 篡改不得冒充原版本完成。
- Reviewer payload：Git 文本 diff 不携带 `GIT binary patch`；binary 文件保留路径/change_type 元数据，视觉内容明确不在一期文本审查范围。
- 集成形态：PyPI 包是唯一 runtime 与产品版本真相源；同仓库 `skills/evidentloop/` 是静态薄编排层，主 `SKILL.md` 只保留宿主无关流程，已验证的宿主专属步骤放在 `references/` 并按需加载；GitHub Pages 提供零安装预览。产品不自研 npm launcher、跨平台独立二进制、宿主 adapter 框架或模型 provider 层。
- Skill 兼容门禁：当前精确要求 package `0.1.0a3`、schema `0.5` 与 prompt `v0.7`；任一不符就在请求的 runtime 操作前停止，不增加兼容别名、迁移器或宽松版本区间。
- 诊断边界：`doctor --json` 返回当前安装环境的实际 `python_executable`，供 Skill 从 PATH 上的 console script 引导同一 runtime；bootstrap 移除 `PYTHONPATH` / `PYTHONHOME` 并禁用 user site，后续 module CLI 使用该绝对路径与 `-I`。非显式 dogfood 时，console 与 interpreter 的原始路径或 canonical target 均不得位于被审计仓库；canonical path 只用于 containment 比较，不替换虚拟环境执行路径。`doctor` 可以提示 `npx` 是否可用，但不扫描宿主私有目录或把文件存在宣称为 Skill discovery；安装异常优先使用标准 skills CLI 与宿主文档诊断。
- demo fixture：使用 wheel 内独立合成资源，在临时 Git 仓库中复用正式主链；不把真实 dogfood 证据作为运行依赖，也不为 demo 新增 diff 输入协议。
- 一期默认输入：本地 Git diff；长期输入按 artifact profile 管理。
- 默认产物：`audit.json` 和 `audit.html`；报告主按钮复制带来源身份的反馈机器块，`audit-feedback.jsonl` 下载为次要入口。
- 中间产物：prepare 在最终目录同父目录创建隐藏 staging workspace，`.run/` 位于其中；成功时目录整体提交，失败时 staging 留作诊断。
- 并发边界：一期按本地单写者、非对抗并发设计。初次报告提交前复查目标 leaf 不存在；反馈修订先生成隐藏 candidate，再用确定性 backup 以目录为单位更新原路径。正常失败恢复旧产物对，突然中断保留可恢复材料；不引入锁、日志系统或指针存储层。
- 隐私权限：POSIX 上尽力将 staging / `.run/` 设为 0700、中间文件设为 0600；精确 mode 不是跨平台退出门禁。

## 一期 code-diff 职责

- `prepare` 选择尚不存在的最终目录，在同父目录 staging 中生成可信 diff 上下文、hunk index 和隐藏审计骨架，并返回 `run_id`、final/staging 路径的结构化 locator。
- Skill 调用宿主 LLM 完成真实语义审查，可用时采用隔离增强，并写入原始审查输出。
- `finalize` ingest 审查结果、生成机械字段、仅在完整性门禁通过时复制转义后的 Overall Assessment 作为语义摘要、执行锚点/引用校验，在 staging 中生成并验证 JSON/HTML；提交前复查目标 leaf 不存在，再用同文件系统目录 rename 成对提交正式产物。目标已存在或 rename 失败时保留 staging 诊断并停止。
- `render` 只消费完整 `audit.json`，不读取 Git 或宿主状态；显式输出路径只授权原子替换该 HTML。
- `revise` 严格校验反馈、来源 audit SHA-256、graph、最新 run、finding 与 fingerprint，追加 `feedback_revision` run，并默认在同一报告路径成对提交新的 JSON/HTML；显式 `--out` 才生成副本。该入口不调用模型，也不修改业务代码。
- `prepare --fix-verification` 只接受用户显式选择的 schema `0.5` 来源报告和当前仍为 `open` 的 finding；先校验 expected/actual report version、来源 diff、finding id/fingerprint 与状态，再读取当前 diff。当前模型独立审查完整新 diff，并为每个目标生成一个含非空 `reason` 的 typed claim；来源只保存直接前驱，不复制旧 runs、不扫描目录、不自动匹配。
- code-diff 的 `audit.json` 保留完整可信 hunk；HTML finding 只显示命中附近的有界可信片段、真实双行号和明确省略标记。精确 diff range 属于 source 元数据，不作为报告主标题。
- HTML 中代码长行不折行；只有内容实际超出时才在最大高度受限的 hunk 容器内横向或纵向滚动，纵向到达边界后继续滚动整页，页面本身不得横向溢出。
- ReviewResult 没有独立修复建议时，adapter 不生成 fix；finding 的原因不能冒充修复动作。HTML 将已有 `requires_fix` 建议就近放入对应问题卡，不另建重复区块；问题卡不展示宽泛 category 徽标，具体类型由标题和原因表达。`dismissed` 问题保留完整内容但使用中性边线、严重度徽标和建议区，不整体降低正文透明度。未精确锚定的 finding 必须保留原因并进入人工分诊语义。
- 变更摘要保留 claim 的模型原判断；只有关联 finding 全部离开 `open` 后，HTML 才派生显示“模型曾判断什么”和“当前裁定是什么”，并使用中性配色。文件问题入口按当前 finding 状态使用“待处理/已忽略/已修复”文案，不改写 claim、edge 或 finding 数据。
- reviewer 输出完整不等于代码获准合并或发布；`review_status`、`verdict` 与 `overall_severity` 分别计算。HTML 把 `pass_candidate` 直译为“无待处理问题”，不扩张其业务含义。

## 状态约定

`review_status` 只描述审查过程，`verdict` 只描述结论，`overall_severity` 只描述当前有效 open findings 的报告级严重程度。`partial` 和 `failed` 均为 `inconclusive`，且 `overall_severity = null`。覆盖率和解析诊断写入 `summary.extensions.evidentloop.review_diagnostics`，不新增核心 `review_coverage`。

schema `0.5` 不保存风险分、风险 delta 或“是否计分”派生状态。完成审查后，只有 `downgraded_from == "bug"` 或缺少可信文件关联的 open finding 时为 `needs_human_triage`；只要还存在其他有效 open finding，verdict 为 `concerns`。

## 当前边界

一期主链路、同 diff 反馈裁定和跨 diff 显式修复验证已经在候选 `audit.json 0.5` code-diff profile 中接通。第二种真实 artifact profile 通过独立 ADR 和 schema 版本扩展，不在一期 schema 中预塞未验证字段。当前不实现自动 finding 匹配、audit series/registry、自动修复、原生 race-proof no-replace、平台专用锁或递归 symlink 防御。

一期实现与发布证据见 `.sopify/history/2026-07/20260710_audit_json_v0_schema_renderer_spike/receipts/`；反馈裁定闭环的决策、任务和验证证据见 `.sopify/history/2026-07/20260716_feedback_revision_loop/`。
