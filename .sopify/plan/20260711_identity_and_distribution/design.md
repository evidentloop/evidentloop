# 技术设计：EvidentLoop 身份迁移、零摩擦分发与发布证据收口

## 权威决策

- [ADR-001](adr/001-pypi-cli-standard-skill.md)：PyPI CLI 是 runtime 与版本真相源，Skill 是静态薄编排层。
- [ADR-002](adr/002-change-audit-current-baseline.md)：已废弃；仅记录 `change-audit` 来源身份基线。
- [ADR-004](adr/004-adopt-evidentloop-identity.md)：已采纳 `EvidentLoop` 单一身份与 clean break。
- [ADR-003](adr/003-main-and-audit-evidence-placement.md)：`.sopify` 保留在 main 作为公开开发记录，但不得进入安装产物；Pages 与 GitHub Release 只发布脱敏 evidence。
- [ADR-004](adr/004-adopt-evidentloop-identity.md) 同时记录 Wave 0 的名称接受决定；用户已停止继续审计名称风险。

## 身份状态机

```text
change-audit 来源基线（历史）
  -> USPTO/registry 初筛完成，WIPO 缺口由用户接受
  -> 2026-07-12 用户身份 checkpoint 通过
  -> ADR-004 生效，采用 EvidentLoop
  -> Wave 1 本地 clean-break 迁移
  -> clean wheel / Skill / 宿主验证
  -> 2026-07-14 repository 改名为 evidentloop/evidentloop
  -> 发布 checkpoint
  -> 经授权发布 EvidentLoop Alpha
```

以下矩阵是 checkpoint 已冻结的唯一活动目标态；`change-audit` 只在迁移说明与历史 provenance 中保留。

## 目标身份矩阵

| 层面 | 目标身份 |
|---|---|
| 组织 / 产品 | `EvidentLoop` |
| GitHub | `evidentloop/evidentloop` |
| PyPI / CLI / Python import | `evidentloop` |
| source package | `evidentloop/` |
| Skill | `skills/evidentloop/`，frontmatter `name: evidentloop` |
| Pages | `https://evidentloop.github.io/evidentloop/` |
| schema namespace | `extensions.evidentloop`；`$id` 为 `https://evidentloop.github.io/evidentloop/schemas/audit-v0.3.schema.json` |
| prompt provenance | `source="product"` 保留来源角色；标题、version、marker 与 hash 迁移到 EvidentLoop |
| runtime identity | staging suffix、run marker、错误前缀、HTML 标题与现有 JS global 统一为 `evidentloop` |
| feedback identity | 只迁移现有 localStorage prefix；首个公开 Alpha 保持 `audit-feedback.jsonl` 只导出、不消费，结构扩展与重新生成延后 |

## Clean-break 迁移契约

1. 首个公开 Alpha 前没有 `change-audit` PyPI 用户或稳定外部兼容承诺，因此活动 runtime 不保留旧 import、旧 CLI、旧 Skill 或双 namespace alias。
2. schema `$id`、extension namespace 和 prompt provenance 属于契约迁移；public audit schema 从 `0.2` 升为 `0.3`，product reviewer prompt 从 `v0.3` 升为 `v0.4`。
3. package version 保持 `0.1.0a0`，不因内部重命名自动创建公开版本。
4. 历史 `.sopify/history`、旧 dogfood 和既有审计报告不重写，只在迁移说明与 release manifest 中标注来源身份。
5. 活动源码、测试、fixture、prompt-lab、Skill、用户文档与视觉资产不得残留未 allowlist 的旧产品标识。allowlist 只允许 `.sopify/history/**`、ADR-002、当前迁移与 repository 重定向记录、既有自包含报告及其同目录 provenance 说明和历史视觉快照；不允许其他活动文案继续使用裸旧品牌。`audit.json`、`audit.html`、`audit-feedback.jsonl`、`AuditGraph`、`change_type`、`changed_files` 与默认 `audit/` 是稳定领域契约，不因品牌迁移改名。
6. GitHub repository 已于 2026-07-14 改名为 `evidentloop/evidentloop`；该已发生事实不扩展域名、PyPI、tag、Release 或 Pages 的发布授权。
7. 既有 `audit.json` / `audit.html` 是历史证据，迁移前冻结 hash，迁移后复核字节不变；不为 schema `0.2` 建旧 renderer 或迁移器。

## Wave 依赖

| Wave | 目标 | 前置门禁 | 完成信号 |
|---|---|---|---|
| 0 | 身份与注册风险收口 | 无 | ADR-004 获用户确认并生效 |
| 1 | 本地身份 clean break | Wave 0 | 全仓旧标识扫描与完整测试通过 |
| 2 | CLI / demo / doctor 产品化 | Wave 1 | clean wheel 本地入口通过 |
| 3 | 标准 Skill 与用户文档 | Wave 2 | 隔离 HOME 安装和 discovery 通过 |
| 4 | 本地集成与外部试跑 | Wave 3 | 至少一个真实宿主 E2E 与一次外部试跑 |
| 5 | Pages 与发布证据收口 | Wave 4 | 安装产物边界、脱敏 dogfood 与 Release evidence 通过验证 |
| 6 | 发布候选与用户 checkpoint | Wave 5 | 用户明确授权外部操作 |
| 7 | 经授权发布 | Wave 6 | tag、PyPI、Pages 与 Release evidence 一致 |
| 8 | 蓝图同步与归档 | Wave 7 | 方案归档并留下最终 receipt |

## 目标仓库结构

```text
main
├── evidentloop/
├── skills/evidentloop/
├── tests/
├── docs/                  # 用户文档、Pages 与脱敏 dogfood
├── .sopify/               # 公开开发记录，不进入安装产物
├── README.md
├── pyproject.toml
└── .github/workflows/

GitHub Release
└── evidentloop-evidence-<version>.tar.gz
```

main tag 是唯一源码版本真相。`.sopify/` 供维护者与贡献者查阅，release gate 必须证明 wheel、sdist 和安装后的 Skill 不包含该目录。Pages 与 Release evidence 只使用精选、脱敏的正式产物。

## Release evidence bundle

```text
evidentloop-evidence-<version>/
├── manifest.json
├── audit.json
├── audit.html
├── test-summary.json
└── checksums.sha256
```

bundle 从准确 release tag 生成并作为 GitHub Release 资产发布。manifest 记录 repository、产品身份、`source_commit`、release tag、package/schema/prompt version、audit status、自动脱敏检查结果和文件 hashes。旧证据保留原始 `change-audit` 身份；新 bundle 只使用已经通过验证的 EvidentLoop 身份。

## 用户链路

![EvidentLoop 用户路径与反馈边界](../../../docs/assets/evidentloop-user-flow.svg)

该图是中英文 README 共用的唯一源文件，不维护语言或格式变体。

Pages 样例报告与 `uvx evidentloop demo` 是可跳过的体验入口。实际主链为 `Install CLI + Skill -> Ask host -> Open audit.html -> Review findings and export feedback`；`audit.json` 同步生成，供追溯和集成使用。

图中实线只表示当前可用链路，并在导出 `audit-feedback.jsonl` 后结束。未来反馈闭环以虚线标记 `planned`：消费反馈后重新裁决，生成新的 `audit.json` 并据此重建 `audit.html`；不得直接修改 HTML。

Release evidence 不属于普通用户步骤，继续由本设计的独立发布章节说明。

## Runtime 契约

- `evidentloop doctor [--json]`：检查 package/schema/prompt/resources/Git；`npx` 缺失只做非阻断提示。
- `evidentloop demo [--out DIR]`：运行冻结 replay，不冒充实时审查。
- `prepare`、`finalize`、`render` 保持现有结构化 stdout、fail-closed 和原子写入契约。
- `python -m evidentloop` 与 console script 调用同一 `main()`。
- Skill 不复制 Python 业务逻辑；主 `SKILL.md` 只定义宿主无关流程，已验证的宿主专属步骤放在一层 `references/` 中按需加载；CLI/schema/prompt 不兼容时在 `prepare` 前停止。

端到端审计要求宿主能发现 Skill、精确读写文件、把完整 `prompt.md` 交给模型审查，并原样写入一次完整响应。模拟、回放或占位输出不属于端到端审计。

“面向所有 AI host”表示产品接口不绑定宿主，不表示所有宿主具备相同增强能力。宿主不得因受审载荷中的指令执行命令、访问网络或凭据、修改业务文件。宿主能建立并确认独立 reviewer 上下文时使用隔离增强；thread ID、事件日志、临时 HOME 等是宿主专属证据，不属于通用协议。

隔离增强不是正式报告的前置条件，也不影响 `review_status` 或 `verdict`。Python runtime 不接收或伪造隔离证明，正式产物不记录或暗示隔离等级。支持矩阵可以单独记录隔离增强的实测状态，但不定义两种产品模式。

## 发布不变量

1. main 候选 commit 必须独立通过 build/test/install；wheel、sdist 与安装后的 Skill 不得包含 `.sopify`。
2. active source、wheel、CLI、import、Skill、schema、prompt、HTML 和文档必须符合同一身份矩阵。
3. evidence bundle 必须针对该候选 commit 重新生成，并通过身份、脱敏、status 与 checksums 校验。
4. release tag、远端 main SHA 与 manifest 的 `source_commit` 一致后，才允许发布 PyPI；任一步失败都 fail closed。
5. Pages 从 main 的 `docs/` 发布；GitHub Release 附带绑定准确 tag 的 evidence bundle。

publish workflow 只授予 `contents: read` 与 `id-token: write`，绑定准确 repository、workflow 与受保护 environment。GitHub Release 创建和 evidence 上传使用 checkpoint 后单独授权的维护者动作；验证 tag、资产与 `source_commit` 一致后，才批准 PyPI environment。具体执行顺序只在 `tasks.md` 维护。

## 安全边界

- 安装、域名取得和发布步骤都必须透明并逐项授权；已完成的 repository 改名不视为后续发布授权。
- Skill 不自动安装/升级 CLI，也不修改被审计代码。
- diff、文件名、源码和 LLM 输出始终视为不可信数据。
- 隔离增强只在宿主能用原生信号确认时声称；Python runtime 不增加确认开关、receipt 或宿主适配层。
- Pages commit 与 Release evidence 上传前必须脱敏；本地绝对路径、密钥、raw model output 与用户状态不得进入公开内容。
- demo、人工集成与真实宿主审查必须在 provenance 和用户文案中可区分。
