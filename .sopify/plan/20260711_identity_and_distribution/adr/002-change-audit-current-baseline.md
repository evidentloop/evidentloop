# ADR-002：change-audit 当前身份基线与重新评估条件

## 状态

已废弃（由 ADR-004 取代）

## 日期

2026-07-11

## 上下文

本 ADR 最初决定 Alpha 保留 `change-audit`，理由是它能直接说明 v0 的 Git diff 审计价值，并可避免当时缺乏证据支撑的品牌迁移。

随后产品边界被进一步澄清：artifact profile 不只处理 change/revision，也允许完整 snapshot、receipt 或其他具备明确审查边界、可验证来源和可信锚点的结构化产物成为正式审查目标；交互式报告还承担反馈、修订与复审闭环。与此同时，产品尚未公开发布、没有需要兼容的 PyPI 用户，当前正是重新评估长期身份成本最低的阶段。

因此，“Alpha 保留 `change-audit`”不再是已经收口的最终决定。本 ADR 只记录现存代码与历史证据的身份基线，并把目标身份决策交给 ADR-004 的注册风险门禁与用户 checkpoint。

## 决策

本 ADR 记录 ADR-004 生效前的仓库身份基线；其中外部资源状态不被描述为已经取得：

| 层面 | 身份 |
|---|---|
| 产品、repository basename、CLI | `change-audit` |
| Python import/source package | `change_audit` |
| Skill | `integrations/agent-skill/change-audit/` |
| PyPI 候选（未取得） | `change-audit` |
| Pages 基线路径（未启用） | `https://evidentloop.github.io/change-audit/` |

当前 v0 仍只宣称 Git diff 审计。不得因为 ADR-004 尚未激活，就把 `change-audit` 推导为首个公开 Alpha 的最终品牌。

2026-07-12 用户明确采用 `EvidentLoop` 并停止继续审计名称风险，ADR-004 随即生效。本表只保留为迁移来源与历史 provenance，不再约束活动身份。

## 理由

- `change-audit` 仍准确记录当前代码、schema、prompt 与历史证据的 provenance。
- 在名称门禁前保持代码不动，可以避免用未核验品牌制造第二次迁移。
- 把“当前事实”与“公开品牌决策”分开，能让分发架构继续推进，同时保留一次低成本、证据驱动的身份选择。

## 替代方案

- 不设门禁立即改为任一候选：拒绝。PyPI、repository、CLI、import 和 schema 同步迁移会放大未经筛查的名称风险。
- 同时维护 `change-audit` 与新品牌 alias：拒绝。双身份增加文档、契约和排障分叉。
- 因为当前代码叫 `change-audit` 就默认公开发布同名 Alpha：拒绝。它把历史惯性误当成已完成的产品决策。

## 影响

- 当前 schema 0.2、`extensions.change_audit`、prompt `v0.3` 和历史证据在 checkpoint 前保持不变。
- ADR-004 已采纳，本 ADR 已废弃；Wave 1 执行一次 clean break。
- 历史 schema 0.2、报告与图仍保留 `change-audit` provenance，不创建运行时 alias。
