# change-audit 长期任务

状态：只保留未完成长期项和明确延后项。当前实施顺序、细分任务与验收门禁以[当前方案包](../plan/20260710_audit_json_v0_schema_renderer_spike/tasks.md)为准。

## 后续能力

- [ ] 根据后续多语言与不同规模样本继续收紧宿主审查 prompt 和语言专项 eval；一期中文正文、协议格式和声明完整性门禁已完成。
- [ ] 评估确定性规则作为 LLM 审查增强，但不替代语义 finding 主链路。
- [ ] 评估多审查者、CrossReview adjudication 和语言专项 eval 对幻觉与漏报的改善。
- [ ] 增加正式 `change-audit` console-script 别名并评估 PyPI 发布；永久保留模块入口。
- [ ] 建模多轮审计差异并消费 `audit-feedback.jsonl`。
- [ ] 按真实需求逐类推进 artifact profile：先允许内部 ReviewResult，只有通过 adapter、可信 anchor、eval baseline 和 renderer profile 四项门禁后才公开正式 audit；候选包括 plan/design、analysis/review-result、agent output、folder diff、远程 PR 和 code snapshot。
- [ ] 评估可选 SVG 概览和 Markdown 导出；完整审计仍以 HTML 为主。
- [ ] 补充 Sopify checkpoint 与其他报告工具的 `audit.json` 消费集成。
- [ ] 真实多写者需求出现后，评估原生 race-proof no-replace、平台专用锁、递归 symlink 防御及对应对抗性故障注入；一期只采用本地单写者、非对抗并发模型。

## 明确延后

- [-] 在 Qoder 手工完成 change-audit Skill 的模型级正向 smoke；本轮只验证 QoderCLI 启动、临时链接和 Skill discovery。
- [-] 自动修复代码或把审计结果升级为强制策略门禁。
- [-] 默认集成模型 SDK、要求用户配置 provider key，或把 provider-backed 模式作为主链路。
- [-] 在用户再次授权前归档、删除 CrossReview 仓库或中断旧包可用性。
