# audit-graph 长期任务

- [ ] 定义并冻结 `audit.json` v0 schema。
- [x] 定义摘要审计字段和 `supports_claim` / `challenges_claim` 边。
- [x] 定义 finding hunk context 字段：`file_path`、`start_line`、`end_line`、`line_side`、`highlight_lines`、`hunk`、`fingerprint`。
- [x] 明确 renderer ownership：LLM/review 只产出 `audit.json` 兼容数据，HTML/CSS/JS/反馈交互/回链校验由固定 renderer 拥有。
- [ ] Renderer-first spike：用最小 `audit.json` 生成单张 finding card，验证 hunk table、装饰条、证据/修复关联和反馈按钮。验收：用 hunk-context-demo 的 finding-001 渲染，产物包含完整 hunk table、橙色装饰条在 highlight_lines 上、inline 关联文本和可点击反馈按钮。
- [ ] 实现 Git diff adapter。
- [ ] 实现 CrossReview `ReviewResult` adapter。
- [ ] 实现 CLI `build` 和 `render`，v0 不实现 `scan`。
- [ ] 实现 HTML renderer，输出带 hunk snippet 和反馈采集的 `audit.html`。验收：用 hunk-context-demo 的 `audit.json` 渲染，产物通过 v0-scope 渲染质量门禁和 data-model HTML 回链校验；产物应在信息架构、finding card 结构、hunk 展示、feedback 控件和 audit trace 属性上与 `docs/examples/hunk-context-demo/audit.html` 设计参考件对齐，不要求逐像素一致。失败降级规则见 v0-scope renderer 常见失败。
- [ ] 实现 `audit-feedback.jsonl` 导出和“复制给 LLM”的 Markdown 决策摘要，v0 不消费反馈。
- [ ] 实现可选 SVG renderer，输出 `audit-graph.svg`。
- [ ] 实现 SVG XML 校验和审计回链校验。
- [ ] 基于真实小/中/大变更重新绘制 SVG 设计样例。
- [ ] 实现可选 Markdown 摘要或修复清单导出。
- [ ] 建模多轮审计快照。
- [ ] 补充 Sopify develop checkpoint 集成说明。
- [ ] 补充 tech-report 消费说明。
