# ADR-003：将 CrossReview 合并为内部 review 子系统

## 状态

已采纳，Wave 0B 迁移复核通过

## 日期

2026-07-10

## 上下文

CrossReview 已实现 ReviewPack、prompt、host-integrated ingest、ReviewResult、normalizer、adjudicator、测试和 eval harness；change-audit 负责 Audit Graph、HTML 与用户反馈。两个项目都处于 alpha 且 CrossReview 没有真实用户。

保持两个包会要求用户安装两次、发现两个 Skill，并维护两套发布和兼容策略。把 CrossReview 作为运行时依赖又会保留这些产品边界。

## 决策

- CrossReview 核心等价迁入 `change_audit.review`。
- ReviewPack 与 ReviewResult 继续作为内部审查契约。
- change-audit 是唯一产品名；CrossReview 是内部能力名。
- 旧 `crossreview` CLI 不进入新 distribution。
- 原测试、eval harness、canonical prompt 和可选 reviewer 行为必须保留。
- 真实 eval fixtures 继续隔离；main 只放 harness 与 synthetic fixtures。
- 迁移先记录基线，再改 import；adapter 在等价迁移完成后实现。
- 旧仓库和 PyPI 包不立即删除、不 yank。

## 理由

现在合并的兼容成本最低，可以把已有审查工程资产直接转化为一个完整用户产品，同时保留内部模块边界和可验证迁移。

## 替代方案

- 两个产品独立发展：拒绝，因为没有用户证明双产品边界有价值。
- change-audit 依赖 `crossreview` 包：拒绝，因为用户仍需承担两包版本协调。
- 复制少量代码、放弃测试与 eval：拒绝，因为会损失现有质量资产。

## 影响

- Wave 0 必须证明 ReviewResult 行为等价。
- import、测试、CI、prompt 资源和可选 extra 都需要迁移。
- 合并 dogfood 成功后才能重新评估旧仓库归档。
- 本 ADR 的实际迁移差异在 Wave 0B 后补充。

## Wave 0B 迁移复核

- 固定源为 CrossReview `99fbe47655b5b4bd8c2c72f4ea6ea92532233705`（`v0.1.0a4`）；旧仓库工作树未修改。
- review 核心、canonical prompt、prompt-lab runner、offline eval harness 和 337 项原测试已迁入 `change_audit.review.*`。
- 迁移前后均为 337 项测试通过；固定 ReviewResult canonical SHA-256 均为 `cfd21093ea762e2afe22d5e5b8dbebe30571bbe34457ba83bd19190d75aab96a`。
- 13 个可重跑 eval fixture 的去路径指标摘要 SHA-256 在迁移前后均为 `001f8a180cf43928766c4da81e9b02f32ac6051cc43cec89748bde6a78641336`。
- 有意差异只有 import namespace、测试目录深度和 distribution 身份；内部 CLI compatibility 模块仅用于保持迁移测试，不注册 `crossreview` console-script，也不成为一期用户命令。
- 真实 eval fixture 与真实 prompt-lab case 未进入 main；当前远端 `eval-data` 不含已发布 33-fixture 汇总所需的全部输出，因此这里只对 13 个可重跑 fixture 声明实测等价，不冒充重新跑过 33 个。
