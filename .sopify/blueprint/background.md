# EvidentLoop 背景

## 产品问题

AI coding 会生成代码变更，也会生成 plan、design、analysis、review-result、final answer 和 agent trace 等产物。审查过程通常散落在聊天、终端和临时 Markdown 中，用户难以确认目标是否可靠、结论依据是什么，也难以把自己的接受、误报或严重度调整带到下一轮。

用户真正需要的是一条可审计链路：把有明确边界的审查目标交给宿主模型，得到可回链 findings，再由已经通过放行门禁的审计适配能力形成结构化审计记录、可交互审计报告和可导出的用户决策。

## 产品愿景

目标是让 AI 辅助开发工作流中任何具有明确审查边界和可验证来源、并能通过相应审计适配能力建立可信锚点的结构化产物，形成可回链、机器可检验的审计记录，并通过可交互审计报告完成检查、反馈、修订与复审。

审计适配能力（artifact profile）定义一类产物如何被采集、定位、验证和呈现。同一种产物可以按本次审计目的成为审查目标、上下文或证据；只有作为正式审查目标且通过放行门禁时，产品才承诺生成完整审计产物：`audit.json` 保存结构化事实与结论，`audit.html` 提供可检查、可反馈、可分享的交互式报告。

## 产品定位

`EvidentLoop` 是面向 AI 变更与可审查产物的可回链审计工具。

- `evidentloop.review` 是 artifact-general 语义审查内核；AI host 的 LLM 负责目标相关的语义判断。
- `evidentloop.audit` 与 renderer 是 profile-specific 正式产品层；只有具备 adapter、可信 anchor、eval baseline 和 renderer profile 的类型，才承诺完整审计产物。
- 产品 runtime 不内置 LLM SDK 或 provider/API key 配置；它负责构造可信上下文、约束审查输出、生成机械字段、校验引用并确定性呈现。
- `evidentloop.review` 直接承载 ReviewPack、prompt、ingest、normalizer 与 adjudicator；迁移来源不形成第二个产品或第二套运行链路。
- Python CLI 是唯一 runtime 与版本真相源；标准薄 Skill 只负责发现和宿主编排。普通用户不需要 clone 仓库、手建 venv、editable install 或手工复制 Skill 目录。

## 用户入口

用户链路按四步递进：先在 GitHub Pages 在线查看真实报告；再用 `uvx evidentloop demo` 运行冻结 reviewer replay；正式使用时通过 `uv tool install evidentloop`（或 pipx）安装 CLI，并通过标准 skills CLI 安装同仓库 Skill；最后在满足能力契约的 AI host 中说“用 EvidentLoop 审计本地改动”。Skill 负责选择 diff 范围、编排宿主 LLM、运行确定性阶段并展示报告路径。用户项目无需复制集成说明或中间契约。

无 AI host 时，`demo` 用冻结输入和 reviewer replay 走通完整机械链并生成明确标记的演示报告。高级集成者也可以手工执行 `prepare -> external review -> finalize`，但产品不提供本地 LLM、provider SDK 或自动模型调用。底层命令是稳定、可调试的集成入口；`review` 仍是 Skill 表达的用户动作，不伪装成脱离宿主即可完成的单命令。

## 目标用户

- 在满足能力契约的 AI coding 宿主中审计本地改动的开发者。
- 需要查看变更摘要、问题证据和修复建议的维护者。
- 需要结构化审计 checkpoint 的自动化工作流。
- 后续需要消费 `audit.json` 或用户反馈的报告与评估工具。

## 核心产物

- `audit.json`：已通过放行门禁的审查目标所对应的正式结构化记录，是审查目标、状态、findings、evidence 和 fixes 的唯一事实来源。
- `audit.html`：具备 renderer profile 时的交互式审计报告；共同外壳保持一致，定位内容按 hunk、section、claim 或其他可信 anchor 呈现，并支持用户检查和反馈 findings。
- `audit-feedback.jsonl`：用户显式导出的结构化决策记录，为后续重新裁决、生成新审计版本和重渲染报告提供输入。

实验性非 diff 类型可以先停在内部 ReviewResult 或宿主摘要，不因此宣称完整 audit 支持。正式产物在同父目录隐藏 staging 中完成校验后成对提交；成功时中间物默认清理。

## 非目标

- 一期不提供 provider SDK，也不要求用户配置模型 API key。
- 不由确定性文本规则替代 LLM 语义审查；确定性规则未来只能作为增强。
- 不自动修改代码，不把审计结论当作发布阻断策略。
- demo/replay 不验证模型质量，不得冒充一次真实 AI 审查。
- 一期不做 folder diff、无 diff artifact 正式审计或远程 PR URL；这些是后续 profile 候选，不是永久排除。
- 一期不做 hosted dashboard、SVG 产品 renderer 或 Markdown renderer；首个公开 Alpha 只记录并导出反馈，不消费 `audit-feedback.jsonl`、不自动修订，完整反馈闭环继续保留为长期能力。
