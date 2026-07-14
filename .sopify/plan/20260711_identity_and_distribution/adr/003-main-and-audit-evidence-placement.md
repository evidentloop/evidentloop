# ADR-003：main 与 audit-evidence 内容边界

## 状态

已采纳

## 日期

2026-07-11

## 上下文

产品面向一键安装和直接使用。用户不需要在默认分支理解 Sopify 蓝图、执行 receipts、dogfood 原始证据或丰富测试输出；需要验证产品可信度的人仍应能公开访问这些材料。本 ADR 的分支边界不依赖最终产品名。

同时，release tag 必须包含可执行测试、schema 和构建门禁，否则 main 无法独立复现产品质量。测试源码和生成型测试产物不能混为一类。

## 决策

1. `main` 只保留产品源码、schema、package 配置、标准 Skill、测试源码与必要 fixture、CI/publish workflow、README 和用户/集成文档。
2. 固定 orphan 分支 `audit-evidence` 保存整个 `.sopify`、公开 dogfood、精选测试摘要、release evidence bundles 与 Pages `docs/`。
3. `.sopify/state`、`.sopify/user`、raw model output、完整日志、coverage、未脱敏截图和 build/dist 不提交到任何长期分支。
4. 维护机使用固定 evidence worktree；main checkout 通过被忽略的本地 `.sopify` symlink 恢复 Sopify。worktree 路径不进入仓库。
5. evidence branch 不含产品源码、不合并回 main，不维护第二个产品版本。
6. `evidence/releases/` 按 tag 和 `source_commit` 追加，不重写；`.sopify` 可以正常演进。
7. README 链接稳定 Pages/分支入口；Release 在 evidence push 后链接确切 evidence commit/path，避免修改 README 导致 `source_commit` 循环失效。
8. 首次 Alpha 发布前完成 `.sopify` 与生成证据的隔离，不把迁移债务带入首个公开 tag。
9. evidence bundle 生成、校验或 push 失败时，阻断 tag 与 PyPI 发布；不提供 best-effort 降级。

## 理由

- 默认分支直接服务安装、阅读和贡献，避免维护过程淹没产品入口。
- 整个 `.sopify` 仍公开可查，符合产品的可信与可追溯方向。
- 测试源码留在 main，使任意 release tag 都能独立运行 CI，不依赖跨分支拉取。
- source/evidence commit 显式绑定，比把生成证据混入产品 commit 更清楚。

## 替代方案

- 所有内容留在 main：拒绝。用户面持续混入蓝图、receipts 和生成证据。
- 测试源码也移到 evidence branch：拒绝。破坏 release tag 的独立可复现性。
- 使用同一长期分支保存产品源码副本和证据：拒绝。会形成双真相源和 merge 漂移。
- 立即建立独立 evidence repository：暂缓。只有同仓库分支出现明显体积、权限或隐私问题时再评估。

## 影响

- 发布增加 main/evidence 两个 commit 及其一致性校验，Git 无法原子更新两者，失败时必须停止 tag/publish。
- 普通 clone 仍可能获取 evidence branch 可达对象；该方案解决默认树和认知隔离，不解决 Git 对象体积。
- 首次迁移必须先在 evidence worktree 完整保全 `.sopify` 与公开证据，再从 main 移除。
- evidence push 前必须执行脱敏和 `source_commit`/checksums 校验。
