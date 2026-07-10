# audit-graph

AI 代码变更的审计链路。

[English](README.md)

AI 写代码很快，AI 审查也能快速发现问题。但审计链路——改了什么、审了什么、确认了什么、还有什么没关——散落在聊天记录和终端输出里。等人终于来读报告时，上下文已经丢了。

`audit-graph` 把审查证据归集为两个可审计产物：机器可读图谱（`audit.json`）和自包含 HTML 审计页（`audit.html`），带代码上下文、证据关联和用户决策控件。

```text
AI coding diff + review signals → audit.json → audit.html → human decision JSONL
```

![audit-graph architecture](docs/assets/audit-graph-architecture.png)

## 当前状态

设计和数据模型已定义。实现代码尚未开始。

## 给谁用

- **AI coding 团队**：合并前需要验证 AI 生成的代码，而不是只看审查摘要。
- **工作流构建者**：在 Sopify 等 AI coding 流程中嵌入审计 checkpoint。
- **独立开发者**：AI 生成并审查代码后，想要一份结构化的审计视图。

## 不做什么

`audit-graph` 不生成 finding、不跑测试、不判断代码是否正确。它可视化来自其他工具的审查信号，让它们可追溯。

## 目标产物

v0 目标 HTML 形态——设计参考，尚未实现。

![v0 target HTML shape](docs/assets/audit-html-preview.png)

## 输入与输出

| 方向 | 文件 | 说明 |
|------|------|------|
| IN | Git diff / staged / unstaged | 变更来源 |
| IN | CrossReview `ReviewResult` JSON | 审查发现 |
| IN | 测试 / lint / typecheck / 扫描结果 | 确定性证据 |
| OUT | `audit.json` | 机器可读审计图谱（真相源） |
| OUT | `audit.html` | 自包含人类审计视图 |
| OUT | `audit-feedback.jsonl` | 用户决策记录（v0 只采集） |
| OUT | `audit-graph.svg` | 可选风险概览图 |
| OUT | Markdown | 非默认导出，用于 PR 或聊天 |

## 审计对象

三类审计问题：

- **变更理解**：改了什么、影响哪些文件、实现路径是否符合原始意图。
- **问题审查**：有没有 bug、风险、遗漏边界或失败证据，哪些 finding 需要修复。
- **用户决策**：确认问题、标记非问题、调整严重度或补充上下文。

一次 AI coding 任务可能经历多轮生成、审查、修复和再审查。`audit-graph` 记录这个收敛过程。

## V0 形态

两个 CLI 命令：

```text
audit-graph build    # 从 diff + 审查输入生成 audit.json
audit-graph render   # 从 audit.json 生成 audit.html
```

每个 finding 渲染为卡片：标题、位置、带关键行高亮的 hunk snippet、证据链、修复建议和用户决策控件。静态 HTML 使用 localStorage 暂存反馈，并导出 `audit-feedback.jsonl`。

## 相邻项目

- [cross-review](https://github.com/evidentloop/cross-review)：独立二次复核。
- [tech-report](https://github.com/sateful-ai/tech-report)：叙事型技术报告生成。
- [sopify](https://github.com/evidentloop/sopify)：工作流编排和 checkpoint。

## License

MIT
