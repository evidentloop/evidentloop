# 任务清单: audit-graph 初始化

目录: `.sopify/plan/20260707_audit_graph_init/`

## 1. 项目骨架

- [x] 1.1 创建 `README.md` 和 `README.zh-CN.md`。
- [x] 1.2 创建 `docs/v0-scope.md` 和 `docs/data-model.md`。
- [x] 1.3 创建空实现目录 `auditgraph/`、`auditgraph/adapters/`、`auditgraph/renderers/`、`tests/`。

## 2. Sopify 知识库

- [x] 2.1 创建 `.sopify/project.md`。
- [x] 2.2 创建 `.sopify/user/preferences.md`。
- [x] 2.3 创建 `.sopify/blueprint/README.md`、`background.md`、`design.md`、`tasks.md`。

## 3. 本次方案包

- [x] 3.1 创建初始化方案包 `background.md`。
- [x] 3.2 创建初始化方案包 `design.md`。
- [x] 3.3 创建初始化方案包 `tasks.md`。
- [x] 3.4 优化文档叙事为 standalone-first、workflow-ready。
- [x] 3.5 补充变更理解、问题审查和多轮审计模型。
- [x] 3.6 写入 SVG 生成策略和 fire skill 借鉴边界。
- [-] 3.7 增加 v0 Audit Graph SVG 设计样例。（已降级：样例未冻结，后续基于真实小/中/大变更重画）
- [x] 3.8 收口默认产物：`audit.json` + `audit.html`，`audit-graph.svg` 可选，Markdown 仅导出。
- [x] 3.9 用本仓库 dogfood 审计文档一致性，补齐 `audit.html` 信息架构，移除 v0 `scan`。
- [x] 3.10 收口摘要审计模型：summary 是 `run/change` 字段，不作为节点类型；通过 claims 边审计摘要准确性。
- [x] 3.11 增加本地仓库 dogfood 示例：`audit.json` + `audit.html`。

## 4. 后续实现

- [ ] 4.1 定义 `audit.json` schema。
- [ ] 4.2 实现 `audit-graph build`。
- [ ] 4.3 实现 `audit.html` renderer。
- [ ] 4.4 实现可选 `audit-graph.svg` renderer。
