# 技术设计: change-audit 正式改名

## 技术方案

- 核心技术: Git 路径迁移、Markdown/HTML/SVG 语义化替换、Python package 命名约定
- 实现要点:
  - 先固化命名契约，再修改引用；不使用无边界的全仓字符串替换。
  - 产品身份与内部模型分层：`change-audit` 是产品，Audit Graph 是数据模型。
  - 当前方案只做命名迁移，不重构 V0 scope、schema 或 renderer 设计。
  - 历史初始化方案保持原始语义，只新增 `20260710_rename_note.md`。
  - GitHub 仓库和本地目录属于外部身份迁移，放在仓库内容校验之后。

## 命名契约

| 层次 | 正式名称 | 迁移规则 |
| --- | --- | --- |
| 产品 / GitHub 仓库 / CLI / PyPI distribution | `change-audit` | 原产品身份 `audit-graph` 迁移为该名称 |
| Python import package / 源码目录 | `change_audit` | `auditgraph` 迁移为该名称 |
| 内部数据模型 | Audit Graph / `AuditGraph` | 保留，不替换为 Change Audit Graph |
| 机器真相源 | `audit.json` | 保留 |
| 人类审计界面 | `audit.html` | 保留 |
| 用户反馈产物 | `audit-feedback.jsonl` | 保留 |
| 未来 renderer 产物 | `audit-graph.svg` | 保留，因为它描述 Audit Graph 模型；当前仓库尚无该文件 |
| 产品架构资产 | `change-audit-architecture.svg/png` | 从 `audit-graph-architecture.*` 迁移并更新引用 |
| HTML 目标预览 | `audit-html-preview.png` | 保留文件名，README 上下文随产品名更新 |

`.sopify/project.md` 是内部命名契约的权威来源。`README.md` 与 `README.zh-CN.md` 只投影用户需要的产品名、定位和命令，不重复解释全部内部规则。

## 迁移设计

### 1. 仓库内身份

- README 标题、项目链接、CLI 示例和 Related Projects 使用 `change-audit`。
- `.sopify/project.md`、blueprint 与当前产品文档中的产品引用使用 `change-audit`。
- `auditgraph/` 目录迁移为 `change_audit/`；规划模块引用迁移为 `change_audit.*`。
- HTML 样张中的 localStorage namespace 等产品级标识迁移为 `change-audit`。
- 产品架构图文件名迁移为 `change-audit-architecture.*`；SVG 只替换可见 `<text>` 节点和可访问 `<title>` 中的产品名，不改 `id`、`class`、`data-*` 等非可见属性，图中的 Typed Audit Graph 术语保留。
- `audit-html-preview.png` 文件名保持不变；README 中围绕该图片的产品文案使用 `change-audit`。

### 2. 保留边界

- `.sopify/plan/20260707_audit_graph_init/` 的目录名和原有正文不做替换。
- 在旧方案包新增 `20260710_rename_note.md`，记录更名日期、新名称和新方案路径；不修改原有 Markdown 正文。
- `audit.json` schema、`audit.html`、反馈格式和未来 renderer 产物 `audit-graph.svg` 不因产品改名变化。
- `.sopify/blueprint/tasks.md` 中未来 SVG renderer 的 `audit-graph.svg` 输出约定继续保留。
- 文档中明确指向内部模型时允许继续使用 Audit Graph。

### 3. 外部身份

```text
仓库内容改名
  -> 本地确定性校验
  -> GitHub repository rename
  -> 更新 origin URL 并验证重定向
  -> 本地目录 audit-graph/ -> change-audit/（最后）
```

GitHub 仓库改名与本地目录改名必须作为独立 checkpoint 执行。目录改名后需要重新打开 workspace，不能在旧 cwd 中继续写文件。

## 验证设计

- 名称验证: `rg` 结果中，旧产品名只允许出现在历史方案、rename note、更名前 dogfood 审计快照、内部模型语境和保留产物名。
- Git 验证: `git diff --check` 通过；staged diff 不包含 `.gitignore` 的既有修改。
- JSON 验证: 所有 `audit.json` 样张通过 `jq empty`。
- SVG 验证: 架构 SVG 与可选 Audit Graph SVG 通过 XML 校验。
- 视觉验证: 在浏览器中检查 `change-audit-architecture.svg` 与 README 目标预览，确认文本替换未破坏渲染。
- HTML 验证: README 和 HTML 中的相对资源链接有效，样张交互 namespace 使用新产品名。
- Python 验证: 不再存在 `auditgraph` import 或源码目录引用，统一为 `change_audit`。

## 知识库同步

```yaml
knowledge_sync:
  project: required
  background: required
  design: required
  tasks: required
```

用户已明确确认正式名称与包名映射，因此 `user/preferences.md` 也需要同步该长期偏好。

## 回滚策略

- 仓库内改名必须形成 `3bd104a` 与 `fac854f` 之后的独立提交链；任一阶段失败时通过 revert 改名提交回到改名前状态，不回退两个基线 commit。
- GitHub repository rename 不能通过本地 Git 回滚，必须在阶段 5 checkpoint 中显式执行或显式改回。
- 本地目录改名失败时停止在新 workspace 之外处理，不在失效 cwd 中继续修改文件。

## 安全与性能

- 安全: 不修改审计数据、不执行生成产物、不触碰凭据；外部仓库改名需显式 checkpoint。
- 性能: 无运行时影响；主要成本是文档、路径和链接一致性校验。
