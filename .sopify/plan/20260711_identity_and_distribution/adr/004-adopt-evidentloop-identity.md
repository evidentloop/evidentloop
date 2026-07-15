# ADR-004：采用 EvidentLoop 单一产品身份

## 状态

已采纳

## 日期

2026-07-12

## 上下文

`change-audit` 准确描述 v0 Git diff 审计，却不能自然覆盖完整 snapshot、receipt 和其他结构化产物作为正式审查目标的长期方向。产品愿景已经明确为：让具备审查边界、可验证来源和可信锚点的 AI 开发产物形成可回链审计记录，并通过交互式报告完成反馈、修订与复审。

`EvidentLoop` 由两个常见词构成：`Evident` 表达依据可检查，`Loop` 表达审查反馈闭环。它可以统一当前单产品组织的 GitHub、repository、PyPI、CLI、Python import 与 Skill 身份，不绑定 code diff、Audit Graph 或 anchor 等单一实现。

Wave 0 的 USPTO 精确检索没有发现 `EVIDENTLOOP` 或 `EVIDENT LOOP`。`Evidence Loop` 与候选名称只相差 `t` / `ce`，但它面向 health outcomes 与 clinical effectiveness evidence；当前产品面向开发者 artifact audit，服务范围、用户与渠道不同。`EVIDENTLY` 与 `EVIDENTLY AI` 是 AI evaluation / monitoring 软件领域的相邻标识，但不是同一名称。

2026-07-12 用户明确要求停止继续审计名称风险并直接采用 `EvidentLoop`。WIPO 未验证作为已接受缺口记录，不再阻断本地身份迁移。PyPI 404、目标 GitHub repository 404 和域名 RDAP 404 仍只代表“未发现”，不代表可注册或已取得；相关外部动作继续受发布 checkpoint 约束。

## 决策

采用 `EvidentLoop` 作为唯一产品身份，并取代 ADR-002。冻结契约如下：

1. 产品、repository 目标、PyPI、CLI、Python import、source package 与 Skill 统一使用 `EvidentLoop` / `evidentloop`。
2. public audit schema 升级到 `0.3`，canonical `$id` 使用 `https://evidentloop.github.io/evidentloop/schemas/audit-v0.3.schema.json`，extension namespace 使用 `extensions.evidentloop`。
3. product reviewer prompt 升级到 `v0.4`；`source="product"` 保持来源角色，标题、run marker、boundary 与 hash 迁移到新身份。
4. package version 保持 `0.1.0a0`；身份迁移本身不制造额外公开版本。
5. 采用 clean break 与既定 allowlist；repository 改名、域名、PyPI、tag、Pages 和发布仍需后续 checkpoint，本决定不授权外部操作。

激活后的身份为：

| 层面 | 身份 |
|---|---|
| 组织 / 产品 | `EvidentLoop` |
| repository | `evidentloop/evidentloop` |
| PyPI / CLI / Python import | `evidentloop` |
| Skill | `skills/evidentloop/` |
| Pages | `https://evidentloop.github.io/evidentloop/` |
| schema | `0.3`；`https://evidentloop.github.io/evidentloop/schemas/audit-v0.3.schema.json`；`extensions.evidentloop` |
| runtime namespace | `evidentloop` |
| prompt provenance | `source="product"` 保持来源角色；标题、version、marker 与 hash 使用 EvidentLoop 身份 |

迁移采用 clean break：不保留旧 import、旧 CLI、旧 Skill 或双 namespace alias。历史 `.sopify`、dogfood 与已生成报告保留原始 `change-audit` 身份，通过迁移说明与 release manifest 维持 provenance。

本 ADR 授权 Wave 1 的本地身份 clean break，但不授权外部注册、远端改名或发布。分支实现的 commit/push 由用户单独授权；迁移期间 `change-audit` 只作为来源身份和历史 provenance 保留，不创建技术 alias。

## 后续状态

GitHub repository 已于 2026-07-14 改名为 `evidentloop/evidentloop`。这是本 ADR 之后发生的外部事实，不扩展域名、PyPI、tag、Release 或 Pages 的授权边界。

## 理由

- 覆盖结构化产物审计与反馈闭环，不把长期产品限制在 change/revision。
- 组织与产品统一，用户只需理解一个名字。
- 两个常见词形成长期隐喻，比 Audit/Anchor/Graph 组合更接近使命而非机制。
- 零用户、未发布阶段适合执行 clean break，避免把双身份兼容债务带入首个 Alpha。

## 替代方案

- 保留 `change-audit`：仍是门禁失败时的安全回退；优点是 v0 直观，缺点是长期 snapshot/profile 需要额外解释。
- `AnchorLoop`：拒绝。anchor 只代表一项机制，域名与历史公司使用也更不利。
- `AuditAnchor` / `AnchorProof`：拒绝。易被理解为区块链或密码学证明，且超出产品承诺。
- `audit-graph` / `audit-everything`：拒绝。前者绑定内部实现，后者暗示无法保证的穷尽性。

## 影响

- 本地迁移涉及 package/import、schema、prompt、runtime identity、Skill、tests、docs 与生成入口。
- repository 改名已经完成；域名取得、PyPI ownership、Trusted Publisher、tag、Release 和 Pages 仍属于后续需授权的外部操作。
- schema 与 prompt 版本必须随实际契约变化升级，建议目标为 schema `0.3` 与 prompt `v0.4`，最终由身份 checkpoint 确认。
- ADR-004 生效后，ADR-002 标为已废弃；ADR-001 与 ADR-003 的分发和 evidence 决策继续有效。
