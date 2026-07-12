# 任务清单：EvidentLoop 身份迁移、零摩擦分发与审计证据隔离

目录：`.sopify/plan/20260711_identity_and_distribution/`

> Wave 0 至 Wave 2 的本地实现与门禁已完成，当前停在 Wave 2 checkpoint；Wave 3 尚未开始。Wave 6 发布 checkpoint 通过前不得改名远端 repository、购买域名、配置 PyPI、push tag、发布或启用 Pages。分支实现的 commit/push 由用户单独授权，不等同于发布授权。

## Wave 0：身份与注册风险门禁（最高优先级）

- [x] 0.1 按 USPTO 官方策略检索 `EVIDENTLOOP`、`EVIDENT LOOP`、相近读音/拼写及相关软件/SaaS 服务；精确候选为 0，近似结果未发现直接冲突。
- [x] 0.2 WIPO Global Brand Database 未取得可验证结果；用户明确接受该缺口并要求停止继续审计名称风险，未伪造“未发现”结论。
- [x] 0.3 已核验 PyPI、GitHub、`.com` / `.dev` RDAP 与相邻品牌状态；`Evidence Loop` 面向医疗研究证据，`Evidently` 面向 AI evaluation / monitoring，均记录为相邻品牌。
- [x] 0.4 冻结 `EvidentLoop` 目标矩阵、schema `0.3` canonical URI、prompt `v0.4`、package `0.1.0a0`、精确 allowlist、历史证据策略与外部动作边界，详见 ADR-004 与 `design.md`。
- [x] 0.5 身份 checkpoint：用户明确采用 `EvidentLoop` 并停止继续审计名称风险；ADR-004 已采纳，ADR-002 已废弃，允许进入 Wave 1。本决定不授权外部改名、注册或发布。

## Wave 1：本地身份 clean break

- [x] 1.1 已生成旧身份清单并冻结精确 allowlist：历史 `.sopify`、历史报告及其 provenance、旧架构/时序快照，以及 Wave 7 前仍真实存在的 remote URL。
- [x] 1.2 distribution、source package、Python import、module entry 与版本读取已统一为 `evidentloop`，未保留 `change_audit` import alias。
- [x] 1.3 public audit schema 已升级到 `0.3`，canonical `$id`、title、`extensions.evidentloop` 与 validator 已同步；旧报告只作为历史证据保留。
- [x] 1.4 reviewer prompt 保留 `source="product"`，标题、version `v0.4`、hash、run marker 及解析逻辑已迁移并由 provenance 测试冻结。
- [x] 1.5 staging suffix、CLI/error prefix、HTML title/kicker、JS global 与 feedback localStorage prefix 已统一；未新增 locator 或 feedback event 品牌字段，领域契约未改名。
- [x] 1.6 活动测试、fixture、prompt-lab 与生成入口已迁移；三个 example 的 6 个历史报告 hash 不变。
- [x] 1.7 活动 Skill 已迁到唯一目录 `skills/evidentloop/`，frontmatter、metadata、触发词与命令已同步，旧 Skill 已删除。
- [x] 1.8 活动 README、核心文档、封面与架构 SVG/PNG 已同步；旧封面删除，历史架构/时序快照字节不变，新图只陈述当前 Git diff 能力。
- [x] 1.9 Python `317 passed`、Ruff、JS、clean wheel、module CLI、schema/prompt probe、旧身份扫描、历史 hash、Markdown 链接、SVG 结构与浏览器视觉验证均通过。最终 clean wheel 只包含 `evidentloop/` 与 dist-info，SHA-256 为 `d7e7d39a6d1eec4f085577d9f0a0f3f6ad5ed7fe5779d97f46c53f8d763ae9b4`。

## Wave 2：Python CLI 产品化

- [x] 2.1 `pyproject.toml` 已增加 `evidentloop` console script 与 Homepage / Repository / Issues URLs；clean wheel 中 console script 与 `python -m evidentloop` help 完全一致。
- [x] 2.2 已实现 `doctor [--json]`，检查版本、schema、prompt、package resources 和 Git；`npx` 缺失只产生非阻断 warning，并输出待 Wave 3 隔离验证的标准 Skill 安装候选、手工 fallback 与下一句请求，不扫描宿主私有目录。
- [x] 2.3 已实现离线 `demo [--out DIR]`：wheel 内独立合成 fixture 在临时 Git 仓库中复用 `prepare -> frozen replay -> finalize`；终端、`audit.json` extension 与 HTML 均明确标记未执行实时 AI 审查。
- [x] 2.4 Python `326 passed`、Ruff、JS 语法/行为、CI YAML、旧身份 allowlist 自动门禁、clean wheel build/install、console/module entry、doctor、demo 与 package resources 均通过。
- [x] 2.5 已审计现有反馈能力并确认首个公开 Alpha 延后反馈消费与重新生成；保留浏览器交互、localStorage 与 `audit-feedback.jsonl` 导出，README 明确边界，未来 Pages 继承同一声明，蓝图继续保留完整闭环长期任务。

## Wave 3：Skill 安装与用户入口

- [ ] 3.1 删除 Codex/Qoder 作为产品前提的表述，改为宿主能力契约和实测支持矩阵；明示 CLI/schema/prompt 兼容范围并在 `prepare` 前 fail closed。
- [ ] 3.2 在隔离临时 HOME 中用标准 skills CLI 从本地 checkout 安装最终 Skill，验证嵌套目录、辅助文件、全局安装形态与 discovery。
- [ ] 3.3 把中英文 README 首次成功路径收敛为“在线看 -> `uvx` demo -> 正式安装 -> 一句话审计”，首版只陈述 Git diff，并补充 uv 主路径、pipx fallback、诊断、更新/卸载和高级人工通道。

## Wave 4：本地集成与外部试跑

- [ ] 4.1 从 clean sdist/wheel 做本地离线安装，验证 CLI、module entry、demo、doctor、package resources、uv tool 本地 wheel 安装与 pipx clean install。
- [ ] 4.2 用本地 wheel 与 `skills/evidentloop/` 至少完成一个宿主的 `Skill discovery -> isolated review -> finalize` 全新环境 smoke；其他宿主不提前宣称已验证。
- [ ] 4.3 用本地 wheel 与 Skill 找至少一名外部试用者走通首次安装与一句话审计，记录阻塞、误解与反馈；不要求 evidence worktree 或公开发布。
- [ ] 4.4 根据 4.2-4.3 修正 CLI、Skill 与文档后重跑 clean wheel、完整测试和真实宿主 smoke。

## Wave 5：evidence worktree 与 Pages

- [ ] 5.1 在本地准备 orphan `audit-evidence` branch 与固定 worktree，写全新机器可复制的 fetch、worktree、symlink、验证、恢复与移除命令，不硬编码绝对路径。
- [ ] 5.2 把整个 `.sopify`、现有 dogfood/生成证据及其引用的旧架构/时序快照一起复制到 evidence worktree；保留旧报告原身份，确认历史链接全部可解析，并确认 state/user、raw output、密钥和本地绝对路径不进入分支，再从 main 移除并加入 ignore。旧快照不得在引用它们的 history 之前单独移走。
- [ ] 5.3 在 `audit-evidence` 建立 `docs/` Pages 入口和 `evidence/releases/<tag>/<source-sha>/` bundle；manifest 必须记录产品身份与版本，永久证据只含脱敏 audit、测试摘要与 checksums。
- [ ] 5.4 验证 main checkout 在没有 evidence worktree 时仍可完整测试、build、安装和运行；验证维护环境通过 symlink 可恢复 Sopify，main 不再跟踪 `.sopify` 或生成型证据。

## Wave 6：发布候选与用户 checkpoint

- [ ] 6.1 新增并本地检查 tag-triggered Trusted Publishing workflow：只授予 `contents: read` 与 `id-token: write`，绑定目标 repository 与受保护 environment，复用 clean build/test 门禁。
- [ ] 6.2 从 clean candidate 生成 README/PyPI/Pages 预览、构建物摘要、完整测试、真实宿主 smoke、身份扫描、脱敏结果与 evidence manifest 草案。
- [ ] 6.3 发布 checkpoint：向用户提交 main/evidence 双侧 diff、准确版本、目标 GitHub 改名、域名动作、PyPI/Trusted Publisher、tag、push、Pages 与 Release 清单；获得明确授权前停止。

## Wave 7：经授权发布

- [ ] 7.1 经授权将 GitHub repository 从 `evidentloop/change-audit` 改名为 `evidentloop/evidentloop`，验证重定向与权限，并更新本地 remote；失败时停止后续发布。
- [ ] 7.2 创建 main release commit，并针对该准确 commit 重跑确定性测试与真实审计；source 有任何变化则废弃候选并重跑。
- [ ] 7.3 在 evidence worktree 生成绑定 7.2 `source_commit` 的 release bundle，验证身份、manifest、audit status、脱敏与 checksums 后创建 evidence commit。
- [ ] 7.4 推送 main 与 `audit-evidence`，验证远端两个 commit、main 内容边界和 manifest 的 `source_commit` 一致；Release 链接确切 evidence commit/path。
- [ ] 7.5 建立 PyPI `evidentloop` 项目所有权并配置 Trusted Publisher；创建与 package version 相同、指向 7.2 main commit 的不可变 tag，由 workflow 发布 Alpha。
- [ ] 7.6 从 `audit-evidence/docs` 启用或刷新 Pages，并从公开入口验证 PyPI README、`uvx evidentloop demo`、`uv tool install evidentloop`、pipx、远程 Skill 安装和确切 evidence commit 链路。

## Wave 8：收口

- [ ] 8.1 在 `audit-evidence/.sopify` 同步 blueprint、project、preferences、history 与最终 receipt；长期蓝图只保留已生效的 EvidentLoop 身份和真实交付状态。
- [ ] 8.2 显式确认后归档当前方案；除方案归档和已授权的 Wave 7 操作外，不额外创建实现或发布 commit，不创建额外 tag 或发布。
