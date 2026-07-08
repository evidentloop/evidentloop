# audit-graph 长期任务

- [ ] 定义并冻结 `audit.json` v0 schema。
- [x] 定义摘要审计字段和 `supports_claim` / `challenges_claim` 边。
- [x] 定义 finding hunk context 字段：`file_path`、`start_line`、`end_line`、`line_side`、`highlight_lines`、`hunk`、`fingerprint`。
- [ ] Renderer-first spike：用最小 `audit.json` 生成单张 finding card，验证 hunk table、装饰条、证据/修复关联和反馈按钮。
- [ ] 实现 Git diff adapter。
- [ ] 实现 CrossReview `ReviewResult` adapter。
- [ ] 实现 CLI `build` 和 `render`，v0 不实现 `scan`。
- [ ] 实现 HTML renderer，输出带 hunk snippet 和反馈采集的 `audit.html`。
- [ ] 实现 `audit-feedback.jsonl` 导出，v0 不消费反馈。
- [ ] 实现可选 SVG renderer，输出 `audit-graph.svg`。
- [ ] 实现 SVG XML 校验和审计回链校验。
- [ ] 基于真实小/中/大变更重新绘制 SVG 设计样例。
- [ ] 实现可选 Markdown 摘要或修复清单导出。
- [ ] 建模多轮审计快照。
- [ ] 补充 Sopify develop checkpoint 集成说明。
- [ ] 补充 tech-report 消费说明。
