# ADR-003：main 与发布证据内容边界

## 状态

已调整

## 日期

2026-07-11；2026-07-15 调整

## 上下文

产品通过 PyPI CLI、标准 Skill 和 Pages 交付，普通用户无需 clone 仓库。`.sopify/` 是公开的开发蓝图、方案和决策记录，不属于 EvidentLoop runtime；它是否位于 `main` 不影响安装链路。

原方案拟用 orphan `audit-evidence` 分支、固定 worktree 和本地 symlink 隔离 `.sopify` 与生成证据。复核后确认，该结构不能减少 Git 对象体积或提高已经公开内容的保密性，却会引入双分支一致性、恢复和发布成本。2026-07-15，用户确认首个 Alpha 保留 `.sopify/` 在 `main`，并以安装产物门禁、脱敏 Pages 和 GitHub Release evidence 收口。

## 决策

1. `main` 保留产品源码、schema、package 配置、标准 Skill、测试、README、用户文档以及公开的 `.sopify/`。
2. `.sopify/` 只记录开发过程，不进入 wheel、sdist 或安装后的 Skill；发布前以文件清单门禁验证。
3. `.sopify/state`、`.sopify/user`、raw model output、完整日志、coverage、未脱敏截图和 build/dist 不提交到长期分支。
4. `docs/` 承载 Pages 内容和精选、脱敏的 dogfood 报告。`.sopify/` 不作为 Pages 内容发布。
5. 每个公开版本从准确 tag 和 `source_commit` 生成 release evidence bundle，校验后作为 GitHub Release 资产发布；bundle 保存 manifest、审计报告、测试摘要和 checksums。
6. 不建立 `audit-evidence` 分支、固定 evidence worktree、`.sopify` symlink 或 main/evidence 双 commit 协议。
7. evidence bundle 生成、校验或上传失败时，阻断 PyPI 发布；不提供 best-effort 降级。

## 理由

- 安装用户只消费 Python 分发包和 Skill，`.sopify/` 留在 `main` 不扩大运行时。
- 维护者与贡献者可以直接查阅蓝图和决策，不需要恢复专用 worktree。
- 单一 main tag 是源码真相；GitHub Release 资产可绑定同一 tag，避免双分支漂移。
- Pages 只发布精选报告，开发记录与公开产品入口保持清楚边界。

## 替代方案

- orphan `audit-evidence` 分支与 worktree：首个 Alpha 不采用。只有后续出现真实的体积、权限或维护问题时再评估。
- 把所有运行态和原始输出留在 main：拒绝。只保留公开、安全的方案与历史记录。
- 建立独立 evidence repository：不采用。当前没有独立权限或生命周期需求。

## 影响

- `.sopify/` 随 GitHub source archive 公开，但不得进入 Python 分发包或安装后的 Skill。
- 发布门禁新增 wheel、sdist 和 Skill 文件清单检查。
- Pages dogfood 与 Release evidence 发布前都必须执行脱敏和 `source_commit`/checksums 校验。
