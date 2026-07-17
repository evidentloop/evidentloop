# 任务清单：反馈裁定闭环

归档目录：`.sopify/history/2026-07/20260716_feedback_revision_loop/`

> 一个方案包、两批实施。Batch A 的两个工程门禁全部通过后才能进入 Batch B；不进入模型复审、自动修复、新 artifact profile 或发布流程。

## Batch A：可信 revision 内核

- [x] A1 冻结来源 audit、四类反馈、撤销、第二轮反馈和人机结论分层 fixture；fixture 必须同时保留模型原判断与当前结论。
- [x] A2 用 fixture 选择 schema `0.4`，只表达反馈 revision、人机判断分层和来源身份，不增加通用迁移模型。
- [x] A3 实现严格 feedback parser，验证字段、类型、时间、动作值和评论边界；畸形或未知字段整体失败。
- [x] A4 实现来源身份校验，覆盖 audit SHA-256、graph、最后一个 run、finding 与 fingerprint；来源变化时返回稳定错误。
- [x] A5 实现反馈归一化与裁定 reducer，支持精确去重、四类动作、撤销和同轮冲突拒绝。
- [x] A6 抽取 summary 纯函数，并用初次审计 fixture 证明现有 verdict、risk score 和计数保持不变。
- [x] A7 实现 revision 变换与语义校验，证明事件、finding 当前状态、summary、来源快照和 run lineage 一致。
- [x] A8 在隐藏 sibling candidate 中生成并验证新的 JSON/HTML；candidate 失败不得接触来源报告。
- [x] A9 实现产物对切换、确定性命名的隐藏 backup、正常失败回滚和中断残留检测；目录中的其他文件保持不变，唯一有效旧报告自动恢复，状态不唯一时返回必要路径。
- [x] A10 增加 `revise SOURCE --feedback JSONL [--out DIR]` 与公开 API；显式 `--out` 只向不存在的新目录提交，并冻结结构化结果和错误契约。
- [x] A11 覆盖恶意评论、冲突、过期来源、验证失败、回滚、模拟中断残留和显式副本测试。

## Batch A 门禁

- [x] CA1：选定的 `0.4` 契约、结构校验和语义校验全部通过。
- [x] CA2：candidate、产物对切换、正常回滚、中断恢复和旧产物对复验全部通过。

主审证据：聚焦测试 `79 passed`，全量测试 `358 passed`；Ruff、核心格式、schema JSON 解析和 `git diff --check` 均通过。

## Batch B：复制给 AI 的入口

- [x] B1 扩展 renderer context 与报告模板，展示模型原判断、人工裁定、当前结论和必要 revision 详情，不从文案猜测状态。
- [x] B2 更新 feedback JavaScript：主 CTA 使用“复制给 AI 更新报告”，生成带来源身份的机器块，并完成新旧 run 浏览器状态换代。
- [x] B3 更新薄 Skill：当前工作区唯一定位、原样临时文件、精确 schema 门禁和失败停止；中断恢复结果必须转换为清晰用户提示。
- [x] B4 更新 README、v0 scope、数据模型和 AI host 集成，只写已实现入口、既定边界与失败恢复，不加入发布流程或未来扩展设计。
- [x] B5 更新 package/Skill 边界测试，完成两轮反馈 E2E，并验证过期载荷停止和显式另存副本。
- [x] B6 运行 Python、Ruff、Node、build、clean-wheel 与 Skill smoke；所有正式门禁必须通过且 wheel 不包含 `.sopify/`。
- [x] B7 使用 EvidentLoop 审计实现 diff，只修复已确认问题；不得因自审扩张本方案范围。
- [x] B8 已同步 `project.md`、`blueprint/design.md` 与 `blueprint/tasks.md`，明确“同路径提交新 revision”取代旧的不覆盖约束；首次归档因用户确认 schema `0.4` clean break 而恢复为活动方案，最终归档等待用户确认后的 finalize。

Batch B 门禁证据：聚焦测试 `67 passed`，全量测试 `365 passed`；Ruff、Node、Skill 校验、`git diff --check`、clean build、release boundary 和 clean-wheel 同路径 revision smoke 均通过。EvidentLoop 自审确认的 2 个问题已最小修复并补回归测试。

## Batch C：schema `0.4` clean break

- [x] C1 冻结两份已提交 `0.3` 报告的 JSON/HTML hash，并确认本地 `audit/` 报告只读保留。
- [x] C2 当前 package `0.1.0a1` runtime 只加载和校验 schema `0.4`；删除 `0.3` package resource、兼容分支与旧字段补齐逻辑，不增加迁移器。
- [x] C3 将活动 fixture、测试、Skill、README、数据模型、host 集成与蓝图统一为 `0.4`；冻结历史报告对和发布证据，当前文档只补只读边界。
- [x] C4 运行 Python、Ruff、Node、Skill、build、release boundary 与 clean-wheel smoke，证明安装包不含 `0.3` schema。
- [x] C5 由独立 Agent 批判审计本地实现、过度设计、用户语言与整体收口，只修复确认问题。
- [x] C6 主 Agent 完成两阶段复审并停在用户确认；确认前不再次归档、不提交、不发布。

Batch C 证据：两份已提交历史报告的 JSON/HTML SHA-256 分别为 `f15fc911…e1d1c / 41b7fa86…eb91` 与 `e9a32fd1…6afb / 0fa59ee9…1328`，工作树未修改这些文件；本地 `audit/` 报告保持只读。聚焦测试 `78 passed`，CLI/Skill 定向回归 `43 passed`，全量测试 `368 passed`；Ruff、Node、Skill、`git diff --check` 和 clean build 通过。clean wheel 为 package `0.1.0a1` / schema `0.4`，不含 `audit-v0.3.schema.json`，doctor、module CLI、demo、同路径 revision 与 release boundary 均通过。独立 Agent 首轮发现 1 个中断恢复阻断和 2 个低严重度收口项，最小修复后复审无 finding，`spec_compliance`、`code_quality`、`user_language` 均通过。

## 完成标准

- 原报告路径默认保持不变，成功后 JSON/HTML 属于同一 revision。
- 人工裁定、模型原判断和当前结论可分别追溯，报告不暗示发生模型复审。
- 过期、冲突或无法唯一定位的反馈失败关闭，不自动猜测、合并或切换来源。
- 正常失败不留下半套正式报告；突然中断保留可恢复材料，下次运行给出确定恢复结果或明确选择提示。
- 三批、完整验证、自审和知识库同步全部完成后，才进入用户确认与 finalize。
