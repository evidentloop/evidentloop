# Hunk context demo

本示例是 v0 代码审计主样张和 design reference，展示 `audit.html` 如何在 finding 旁嵌入代码变更上下文（hunk snippet），并采集用户审计决策。

场景：

- 目标：审计 auth token refresh 修复是否完整。
- 输入：`HEAD~1` 的本地 Git diff。
- 输出：`audit.json`（含 hunk context）和 `audit.html`（带代码上下文的审计视图）。
- 可选输出：用户在 HTML 中导出的 `audit-feedback.jsonl`。

核心设计点：

- **hunk 嵌入 audit.json**：finding 节点包含 `hunk` 字段，由 build 阶段的 gitdiff adapter 从 Git 提取。renderer 不直接读 Git。
- **扁平 finding 字段**：finding 直接包含 `file_path`、`start_line`、`end_line`、`line_side`、`highlight_lines`、`hunk`、`fingerprint`。
- **finding card**：每个 finding 展示为一个卡片，包含标题、位置、diff 代码块、证据和修复建议。
- **代码装饰条**：hunk 左侧有橙色竖线标记 `highlight_lines` 指定的关键行。
- **diff 着色**：绿色底 = 新增行，红色底 = 删除行，无底色 = 上下文行。
- **本地跳转**：HTML 可以由 renderer 生成编辑器跳转链接，但链接不写入 `audit.json`。
- **反馈采集**：HTML 可以用 JavaScript + localStorage 暂存用户决策，并导出 JSONL；v0 不消费该 JSONL。
- **审计回链**：所有可视元素保留 `data-node-id` / `data-claim-id`。

该示例不是 renderer 产物，也不是可直接复制的模板源码。实现 renderer 时应参考它的视觉结构、CSS 思路和反馈交互，但 sections、metrics、finding cards、hunk table 和 edges 关系都必须由 `audit.json` 数据驱动生成。

文档审计样张见 `../dogfood-local-repo/`。
