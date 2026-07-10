# 变更提案: change-audit 正式改名

## 需求背景

当前项目以 `audit-graph` 为名，但产品形态已经收敛为面向 AI 代码变更的本地审计工具：它把 Git diff、审查发现、确定性证据和用户决策归一化为 `audit.json`，再生成 `audit.html`。Audit Graph 是内部有向数据模型，不是默认用户界面；继续使用 `audit-graph` 作为产品名会放大 graph UI 和通用图谱工具的错误预期。

用户已确认将 `change-audit` 作为正式工具名，而不是临时 V0 名称，并统一仓库、CLI、PyPI distribution 与 Python import。改名前的产品设计变更已通过 commit `3bd104a` 独立保存，避免与迁移 diff 混合。

评分:
- 方案质量: 9/10
- 落地就绪: 8/10

评分理由:
- 优点: 命名契约、保留项、历史边界、验证门禁和外部改名顺序均已明确。
- 扣分: GitHub 仓库与本地目录改名仍需要执行时的外部确认和 workspace 重开。

## 变更内容

1. 将产品、仓库、CLI 和 PyPI distribution 统一命名为 `change-audit`。
2. 将 Python import package 与源码目录统一命名为 `change_audit`。
3. 将 Audit Graph / `AuditGraph` 固化为内部数据模型名。
4. 保留 `audit.json`、`audit.html`、`audit-feedback.jsonl`，以及未来 renderer 产物 `audit-graph.svg`；后者描述 Audit Graph 模型，不是当前产品架构资产。
5. 以 `.sopify/project.md` 作为命名契约真相源，README 只做公开投影。
6. 对当前 README、blueprint、v0 scope、data model、样张和架构资产执行语义化改名。
7. 不重写 `.sopify/plan/20260707_audit_graph_init/` 的历史内容，只新增 `20260710_rename_note.md` 记录后续更名。
8. 仓库内容完成并通过校验后，再改 GitHub 仓库与 remote；本地目录最后处理。

## 影响范围

- 模块: project contract, README, Sopify blueprint, docs, examples, Python scaffold, CLI examples, architecture assets, repository identity
- 文件: 当前约 18 个文件、97 处产品名引用，以及 `auditgraph/` 源码占位目录
- 基线: 产品设计变更已提交为 `3bd104a`；全局 Qoder ignore 调整已独立提交为 `fac854f`

## 风险评估

- 风险: 机械全量替换会误改 Audit Graph 模型名、产物名和历史方案记录。
- 缓解: 使用显式命名映射和允许保留旧名白名单，逐类修改并以 `rg` 复核。
- 风险: 改 GitHub 仓库或本地目录过早会破坏当前 workspace、remote 和外部链接。
- 缓解: 外部身份在内容迁移完成后单独执行，本地目录始终最后改。
- 风险: 迁移提交出现问题时，仓库内容和外部身份可能难以区分回滚边界。
- 缓解: 以 `3bd104a` 与 `fac854f` 为改名前基线；仓库内改名使用独立提交，可通过 revert 该提交链回退。GitHub 仓库改名必须在独立 checkpoint 执行。
