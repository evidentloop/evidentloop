# EvidentLoop 长期任务

状态：只保留未完成长期项和明确延后项。一期实施任务与验收证据见[已归档方案包](../history/2026-07/20260710_audit_json_v0_schema_renderer_spike/tasks.md)。

## 后续能力

- [ ] 根据后续多语言与不同规模样本继续收紧宿主审查 prompt 和语言专项 eval；一期中文正文、协议格式和声明完整性门禁已完成。
- [ ] 评估确定性规则作为 LLM 审查增强，但不替代语义 finding 主链路。
- [ ] 评估多审查者、二次 adjudication 和语言专项 eval 对幻觉与漏报的改善。
- [ ] 把 Python 包产品化为 PyPI CLI：增加 console script、`doctor --json` 和冻结 reviewer replay 的 `demo`；doctor 不扫描宿主私有目录，demo 使用 wheel 内独立合成 fixture 并明确 provenance。
- [ ] 用 `skills@latest` 验证仓库嵌套 Skill 与辅助文件可完整安装；不自研 npm launcher、独立二进制、宿主 adapter、MCP 或模型 provider 层。
- [ ] 按 `evidentloop` CLI 重写 README 首次成功路径为“在线看 -> `uvx` demo -> uv/pipx 安装 -> 标准 skills CLI -> 一句话审计”，并用 GitHub Pages `audit-evidence/docs` 发布轻量入口。
- [ ] 验证 uv、pipx clean install 和至少一个真实宿主的 `Skill discovery -> isolated review -> finalize`；只声明实测通过的宿主与平台。
- [ ] 为 PyPI `evidentloop` 配置 Trusted Publisher，发布前创建同版本不可变 Git tag；GitHub Release 页面可选，未经授权不发布。
- [ ] 建模多轮审计差异并消费 `audit-feedback.jsonl`。
- [ ] 按真实需求逐类推进 artifact profile：先允许内部 ReviewResult，只有通过 adapter、可信 anchor、eval baseline 和 renderer profile 四项门禁后才公开正式 audit；候选包括 plan/design、analysis/review-result、agent output、folder diff、远程 PR 和 code snapshot。
- [ ] 评估可选 SVG 概览和 Markdown 导出；完整审计仍以 HTML 为主。
- [ ] 补充 Sopify checkpoint 与其他报告工具的 `audit.json` 消费集成。
- [ ] 真实多写者需求出现后，评估原生 race-proof no-replace、平台专用锁、递归 symlink 防御及对应对抗性故障注入；一期只采用本地单写者、非对抗并发模型。

## 明确延后

- [-] 在 Qoder 手工完成 EvidentLoop Skill 的模型级正向 smoke；本轮只验证 QoderCLI 启动、临时链接和 Skill discovery。
- [-] 自动修复代码或把审计结果升级为强制策略门禁。
- [-] 在 Python 包集成模型 SDK、provider/API key 配置或 standalone reviewer；模型执行只由 AI host 承担。
- [-] 在用户再次授权前归档、删除 CrossReview 仓库或中断旧包可用性。
