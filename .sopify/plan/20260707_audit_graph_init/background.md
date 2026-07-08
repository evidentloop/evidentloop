# 变更提案: audit-graph 初始化

## 需求背景

当前已有 `cross-review` 负责隔离上下文二次复核，`tech-report` 负责生成结构化技术报告。新的 `audit-graph` 需要作为平级独立项目，补上“可视化审计证据图谱”这一层。

AI coding 用户一次任务可能改动很多文件，也可能反复经历生成、审查、修复和再审查。`audit-graph` 应优先支持独立审计，也可以作为 Sopify 等工作流中的审计 checkpoint。

本次任务只做初始化：创建项目文档骨架、长期 Sopify 蓝图、本次方案包和空实现目录，不添加实现代码。

评分:
- 方案质量: 8/10
- 落地就绪: 8/10

评分理由:
- 优点: 边界清晰，避免和 CrossReview、tech-report 重叠。
- 扣分: 尚未通过真实审计样例验证数据模型。

## 变更内容

1. 创建 `audit-graph` 平级项目目录。
2. 创建 README、v0 scope、data model 文档。
3. 创建 `.sopify` 长期蓝图。
4. 创建本次初始化方案包。
5. 创建空实现目录，保留后续实现落点。
6. 明确审计分为变更理解和问题审查两层。
7. 明确默认产物为 `audit.json` 和 `audit.html`，`audit-graph.svg` 为可选概览图。
8. 明确 SVG 只做单一 Audit Graph 模板。

## 影响范围

- 模块: documentation, Sopify blueprint, project scaffold
- 文件: README、docs、`.sopify`、`.gitkeep`

## 风险评估

- 风险: 名称和职责仍可能被误解为 CrossReview 的替代品。
- 缓解: 在 README 和 blueprint 中明确 `audit-graph` 消费 CrossReview 结果，不替代 reviewer。
