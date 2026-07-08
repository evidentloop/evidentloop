# 技术设计: audit-graph 初始化

## 技术方案

- 核心技术: 计划使用 Python CLI，默认生成本地 HTML，可选生成静态 SVG。
- 实现要点:
  - 当前只生成项目结构和文档，不实现 Python 模块。
  - `.sopify` 记录长期产品边界和后续任务。
  - `docs/` 记录 v0 范围和数据模型，便于后续实现按契约推进。
  - 产品叙事采用 standalone-first、workflow-ready。
  - 审计模型同时覆盖变更理解和问题审查。
  - SVG 渲染只定义单一 Audit Graph 模板。

## 架构设计

```text
audit-graph/
  README.md
  README.zh-CN.md
  docs/
    v0-scope.md
    data-model.md
  auditgraph/
    adapters/
    renderers/
  tests/
  .sopify/
    blueprint/
    plan/20260707_audit_graph_init/
    user/
```

## 审计模型

```text
run
  -> change
  -> files
  -> findings
  -> evidence / fixes
```

多轮任务通过多个 `run` 快照表达：

```text
initial audit -> fix audit -> final audit
```

## SVG 策略

SVG renderer 只消费结构化图谱，不直接消费自然语言或 Markdown。

```text
audit.json
  -> 固定 Audit Graph 模板
  -> audit-graph.svg
  -> XML 校验
  -> 审计回链校验
```

本项目只借鉴 fire skill 的模板化生成、XML 校验和可选 PNG 导出，不借鉴多图种、多 style 和通用画图路线。SVG 是可选概览图，完整审计阅读由 `audit.html` 承担。

## 模块边界

- `docs/`: 产品和技术契约。
- `auditgraph/`: 后续 Python package 落点，当前仅占位。
- `auditgraph/adapters/`: 后续输入适配器落点。
- `auditgraph/renderers/`: 后续 SVG、HTML、Markdown renderer 落点。
- `tests/`: 后续测试落点。
- `.sopify/`: 长期蓝图和本次方案包。

## 安全与性能

- 安全: v0 初始化不读取外部密钥，不调用网络，不执行审计命令。
- 性能: 当前仅文档和目录初始化，无运行时性能影响。
