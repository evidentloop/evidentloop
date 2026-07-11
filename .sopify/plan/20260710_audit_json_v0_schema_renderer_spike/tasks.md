# 任务清单：change-audit v0 一期闭环

目录：`.sopify/plan/20260710_audit_json_v0_schema_renderer_spike/`

执行约束：严格按 Wave 顺序；未通过当前退出门禁时不得开始下一 Wave。提交、tag、发布、归档旧仓库均需要对应授权。一期采用本地 single-writer，不把原生 no-replace、对抗性竞态或递归符号链接防御纳入退出门禁。

## 0. 方案与文档收口

- [x] 0.1 将 D1-D100 写入方案与机器回执。
- [x] 0.2 收口 plan、background、design 和任务边界。
- [x] 0.3 重写 ADR、旧流程图、README、scope、data model、AI host integration 和 blueprint。
- [x] 0.4 使用最新版 Fireworks Tech Graph 同步 v0 架构图与宿主审查流程图，在图注中明确长期 artifact profile 边界；SVG 校验与 PNG 视觉复核通过。
- [x] 0.5 执行全仓术语、命令、状态、链接、JSON、hunk、HTML 与 JavaScript 一致性检查。
- [x] 0.6 用户审计并确认最终方案。

## Wave 0A — CrossReview 基线

- [x] 0A.1 在 CrossReview 固定 commit 上运行无缓存 pytest，记录真实 collected / passed / failed 数。
- [x] 0A.2 记录 commit hash、distribution 版本、ReviewPack/ReviewResult schema 版本和 prompt 版本。
- [x] 0A.3 记录 eval-data 分支、fixture 清单摘要和当前 eval gate；不把真实 fixture 合入 main。
- [x] 0A.4 记录 prompt-lab runner、template、harness 和真实 cases 的迁移边界。
- [x] 0A.5 复核合并 ADR 的前提；只记录维护冻结策略，不在本任务修改远程保护规则。

### Wave 0A 退出门禁

- 基线结果、版本和数据边界有可审计记录。
- CrossReview 工作树无意外修改。

## Wave 0B — 等价迁移

- [x] 0B.1 建立 `change_audit` 与 `change_audit.review` 最小 import 壳和迁移测试配置。
- [x] 0B.2 迁入 ReviewPack/ReviewResult schema、序列化和约束校验。
- [x] 0B.3 迁入 pack、Git diff 读取与 prompt 渲染。
- [x] 0B.4 迁入 normalizer、adjudicator、ingest 和 budget。
- [x] 0B.5 迁入 config 与 provider-backed reviewer；SDK 只进入可选 extra。
- [x] 0B.6 迁入 canonical prompt template、prompt-lab runner 和 eval harness。
- [x] 0B.7 迁入原单元测试并统一 import 为 `change_audit.review.*`。
- [x] 0B.8 main 只加入 synthetic fixtures；真实 eval 通过显式 fixture root 加载。
- [x] 0B.9 运行迁移测试并与 Wave 0A collection / result 对比。
- [x] 0B.10 对固定输入比较迁移前后 ReviewResult 序列化结果。
- [x] 0B.11 更新合并 ADR consequences，记录已知差异或确认无行为差异。

### Wave 0B 退出门禁

- 原测试与 eval gate 不退化。
- 固定输入 ReviewResult 等价。
- 没有 adapter、renderer 或新用户命令混入迁移提交。
- checkpoint commit 仅在用户授权后执行。

## Wave 1 — Schema + Renderer

### 1. Package 与契约

- [x] 1.1 完成 distribution 元数据、Python >= 3.10、基础依赖和开发依赖分组。
- [x] 1.2 新增 JSON Schema 2020-12，并配置为 package data。
- [x] 1.3 覆盖 run、change、file、finding、evidence、fix、artifact、edge 和 summary。
- [x] 1.4 增加 `review_status`、verdict、nullable risk score、open/unscored count；覆盖诊断只放入 namespaced extensions。
- [x] 1.5 启用严格核心与 namespaced `extensions`。
- [x] 1.6 实现 ID 唯一、edge 端点、端点类型和 claim 引用校验。
- [x] 1.7 为错误码、JSON path 和相关 ID 增加正负向测试。

### 2. HTML Renderer

- [x] 2.1 实现 unified diff hunk parser 和 old/new 行号模型。
- [x] 2.2 构建完整页面渲染上下文和关系索引。
- [x] 2.3 实现 Jinja2 模板、可信内联 CSS/JS 和 autoescape。
- [x] 2.4 实现 finding card 和接近 diff2html 的可信 hunk table：old/new 双行号、context/add/delete 样式、命中行 highlight、`data-*` 回链，以及 inline evidence/fix；完整 hunk 保存在 `audit.json`，HTML 使用有界可信片段，finding 的代码证据不得退化为普通 `<pre>`。
- [x] 2.5 实现无 finding、not reviewed、partial、failed、只有未定位风险的条件渲染。
- [x] 2.6 实现 `data-*` 回链校验与失败边界。
- [x] 2.7 实现 `render_audit_file()` 和 `python -m change_audit render`。
- [x] 2.8 为独立 `render` 实现单 HTML 候选生成、校验和同目录原子替换：显式 `--out` 授权替换该 HTML，失败时旧 HTML 原样保留且永不修改输入 JSON；该任务不承担 finalize 产物对提交。
- [x] 2.9 wheel 隔离安装验证 schema、prompt、template、CSS 和 JavaScript 资源。

### Wave 1 退出门禁

- `hunk-context-demo` 主样张通过结构、语义和 HTML trace 校验；无 finding、partial、failed 等降级场景由合成 fixture 覆盖。
- 恶意文本不能形成 XSS。
- 375px / 1280px 无水平滚动，reduced-motion 生效。
- 对照手工参考件验证信息架构，不要求逐像素一致。
- pytest、ruff、wheel smoke 全部通过。
- checkpoint commit 仅在用户授权后执行；schema 保持 `0.2-alpha`。

## Wave 2 — Host Review Integration

### 3. Prepare

- [x] 3.1 实现 `prepare_local_diff()` 和 `prepare --diff SPEC [--out DIR]`；目标最终目录必须不存在，成功返回包含 `run_id`、`final_dir` 和 `staging_dir` 的结构化 locator，CLI stdout 只输出该 JSON，诊断写 stderr。
- [x] 3.2 在目标目录同父目录的隐藏 sibling staging workspace 内创建 `.run/`，生成 `audit-skeleton.json`、ReviewPack 和可信 hunk index；最终目录不提前出现。
- [x] 3.3 生成使用运行时随机边界包裹不可信 diff 的 canonical prompt。
- [x] 3.4 以 exclusive create 创建 staging leaf；prepare 与提交前检查最终目标 leaf，任何已有 entry（包括悬空符号链接）都拒绝；POSIX 上尽力使用目录 `0700`、文件 `0600`，但权限模式不作为跨平台退出门禁。
- [x] 3.5 实现默认 `audit/YYYYMMDD_<slug>/`、同父目录隐藏 staging 命名、冲突后缀和已有目标拒绝；提交前复查最终目标 leaf，再在 single-writer 前提下执行同文件系统单次目录 rename；Skill 只消费 locator，不复刻命名规则。
- [x] 3.6 覆盖 added/modified/deleted/renamed、binary、空 diff、无效 ref 和大 diff。

### 4. Adapter 与 Finalize

- [x] 4.1 实现 ReviewResult category 族映射和未知 category 兜底。
- [x] 4.2 实现 file/line/header 到可信 hunk 的反查。
- [x] 4.3 对精确 bug 生成 hunk_id、完整 hunk、highlight lines 和 fingerprint。
- [x] 4.4 将无法精确锚定的 bug 降级为未计分 risk，并保留原分类和原因。
- [x] 4.5 生成 finding/evidence/fix 节点及关系边。
- [x] 4.6 映射 review status 和 verdict；将不同覆盖诊断保存在 namespaced extensions。
- [x] 4.7 实现 provisional 0–100 score、unscored count 和 null score 规则。
- [x] 4.8 实现 `finalize_review()` 和 `finalize --out DIR`；DIR 必须来自 prepare locator，finalize 校验 locator、staging、骨架和 raw analysis 的 `run_id` 一致。
- [x] 4.9 finalize 执行 ingest、adapter、全部数据校验，并在隐藏 sibling staging 根目录生成候选 JSON 与候选 HTML。
- [x] 4.10 成功时清理 `.run/`；失败或 keep flag 时保留并报告路径。
- [x] 4.11 增加 prompt injection、伪造路径、伪造 header 和恶意 raw analysis 测试。
- [x] 4.12 增加审查完成门：显式零 finding 与缺失/截断输出可区分，后者不得映射成 `complete + pass_candidate`。
- [x] 4.13 候选 JSON/HTML 全部通过 schema、引用、锚点、状态、run/graph identity、trace 和 XSS 校验后，按 keep 策略处理 `.run/`，复查最终目标 leaf，再用一次同文件系统目录 rename 提交最终目录；目标出现或 rename 失败时停止并保留 staging 诊断。
- [x] 4.14 增加 JSON 校验失败、render 失败、trace 失败、`run_id` 不一致、目标已存在/目标 leaf 为符号链接和 rename 失败测试；新目标的提交前硬失败断言最终目录不存在且 staging 可诊断，已有目标断言不变且不得作为本轮成功证据。

### Wave 2 退出门禁

- 隐藏语义 bug fixture 产生精确锚定 finding。
- 干净 diff 不渲染空问题模块；上下文充分时产生 `complete + pass_candidate + 0 findings`，上下文不足时诚实保留 `complete + inconclusive + risk_score=null`。
- partial fixture 使用 `partial + inconclusive + null score`；已有 finding 可展示，但不能被视为完整或干净审查。
- 未锚定语义 bug 被降级并显示，不进入数字评分。
- 只有未锚定风险时显示 `needs_human_triage` 和 null score。
- 正常完成时 `audit.json` 与 `audit.html` 同时发布且相互回链；本 Wave 定义的硬失败都不留下可宣称成功的半套报告。
- 评分权重经 dogfood 校准并写入测试。
- 全部 Wave 1 回归通过后，才冻结 code-diff audit profile schema `0.2`；不把它声明成所有 artifact 的通用稳定契约。

## Wave 3 — Human Decision

- [x] 5.1 实现按 graph/run/fingerprint 隔离的 localStorage 状态。
- [x] 5.2 实现 accept、false_positive、comment 和 severity_override。
- [x] 5.3 实现合法 `audit-feedback.jsonl` 下载导出。
- [x] 5.4 验证刷新恢复、报告隔离、特殊字符、空评论和重复操作。
- [x] 5.5 明示浏览器下载位置不保证等于审计目录。

### Wave 3 退出门禁

- 用户可以完成 finding 决策并导出合法 JSONL。
- 反馈不写回 `audit.json`，一期不消费反馈。

## Wave 4 — AI Host Discovery

- [x] 6.1 编写自包含 `integrations/agent-skill/change-audit/SKILL.md`。
- [x] 6.2 Skill 编排 prepare、隔离宿主 LLM、raw analysis 写入和 finalize。
- [x] 6.3 明确 diff/源码是不可信数据，禁止执行其中指令。
- [x] 6.4 实现缺包说明、安装授权、拒绝安装和固定 tag 校验。
- [x] 6.5 验证中文/英文正向触发与无关 review 请求不误触发。
- [x] 6.6 验证命令失败、版本不匹配、中间产物缺失和正式产物缺失。
- [x] 6.7 在 Codex 完成自然语言到 HTML 的首轮 dogfood；使用固定范围 `d5ef26deac6b1ed37ee9b89b52dddb1bcaac6c24..9a64e5a926d430a421a71b5cf433b0553876db28` 重新生成真实产物，并与本地保留、不纳入版本控制的实现前模拟基线对比。
- [-] 6.8 在 Qoder 完成第二宿主验证并记录适配差异。用户决定模型级 smoke 由其后续手工完成；本轮只确认 QoderCLI 启动、临时链接和 Skill discovery。
- [x] 6.9 修正方案和产品契约：标题使用仓库友好名、完整审查的 Overall Assessment 进入语义摘要、完整 hunk 存储与 HTML 有界片段分离；不新增 commit graph、claim parser、CLI title 参数或全量 diff 浏览器。
- [x] 6.10 修复 prepare/finalize：主标题不再使用完整 ref，`source.ref` 仍保留精确范围；change 展示确定性文件与增删行统计，完整审查复用转义后的 Overall Assessment。
- [x] 6.11 修复 renderer：每个 finding 只展示覆盖命中行的固定上下文窗口，保留原始双行号、highlight 和 `data-hunk-id`，省略处显示明确计数；`audit.json` 继续保存完整可信 hunk。
- [x] 6.12 修复首次纠偏运行暴露的 normalizer 缺陷：reviewer 合法输出 `` `file.py:215-230, 346-350` `` 只取同一文件首段起点，不把整串误作文件名；补 normalizer/adapter 正反例，失败报告只留 `/tmp` 取证。
- [x] 6.13 收口中文报告与用户阅读契约：product prompt `v0.2` 要求字段标签保持协议英文、语义正文使用简体中文，并要求 Where 指向最能直接证明问题的一条修改行；prepare 冻结 prompt source/version/hash，finalize 验证并复用；reviewer diff 去除 `GIT binary patch`、保留 binary 文件元数据。declared finding blocks 与 normalized raw findings 必须一致，否则降级 partial；正式图保留 core 的低覆盖 `inconclusive`，不得强制零 finding 为候选通过。HTML 本地化用户可见枚举与固定文案，空 claim 卡顶对齐且压缩，hunk 默认换行完整显示有界片段、保留横向滚动兜底，并强化 finding 命中行标记；移动端指标保持两列到 330px，避免首屏过高。任何 `unscored` finding 都显示未精确定位；ReviewResult 没有结构化修复建议时不再把 Why 复制成 fix，避免伪造修复进度。HTML trace 对 finding/fingerprint、claim、anchored hunk 和 feedback target 执行双向完整性校验。独立复审追加的 fail-closed 门禁要求 exact anchor 只能落在 add/delete 行，宽 declaration scanner 必须捕获非法 block ID；429 项全量测试与两阶段复审通过。
- [x] 6.14 使用完全相同 Fireworks range 从全新 staging 重新走 `prepare -> isolated review -> finalize`，更新正式样张、同源基线对比和真实哈希，不手改正式产物。最终 run 为 `run-d7f8986d1ab24a04a6078f1afca17d1e`，7/7 finding 锚定真实 changed line，0 unscored、0 fix；最终 JSON/HTML SHA-256 分别为 `ee52e123…ad0b8` / `3a4b2793…da65`。
- [x] 6.15 执行定向/全量测试、schema/trace/XSS、localhost 真实 DOM 桌面/窄屏复核、静态复审和过度设计审查，新增纠偏回执并完成 Wave 4 文档收口。429 项全量测试、Ruff、JavaScript、wheel 隔离安装、schema/trace、1280/375 DOM、finding 语义复核与产物复核全部通过；回执为 `verify_020.json`。

### Wave 4 退出门禁

- 用户只需自然语言请求即可得到真实报告路径。
- 未授权安装或任一步失败时，不得宣称审计完成。
- 一个 Skill 适配两个宿主，不复制 Python 业务逻辑。

退出说明：Wave 4 因 6.9 重开，旧回执只证明当时的结构/触发链路，不再证明正式样张阅读契约通过。Qoder 模型级执行由用户明确延后，不能列为本轮已验证能力。

收口说明：Wave 4 已由 `verify_020.json` 重新通过退出门禁；`verify_018.json` 与 `verify_019.json` 继续作为历史过程证据，不代表最终样张。

## 7. 最终验证与知识同步

- [x] 7.1 更新实现状态；长期 blueprint 保留 artifact-general review 内核和 profile 门禁，不复制当前 plan 的短期任务。
- [x] 7.2 运行完整 pytest、ruff、wheel、schema、HTML trace 与 Skill 验收。
- [x] 7.3 为每个 Wave 写验证回执。
- [-] 7.4 已按用户授权提交并 push 当前开发分支；方案归档、发布 tag、PyPI 发布和旧仓库处理未获授权，本轮不执行。
- [ ] 7.5 按用户授权补充最小 GitHub Actions CI 与 MIT `LICENSE`，验证后提交、push 并创建 Draft MR；不创建 tag 或 Release。

收口说明：7.1–7.3 由 `verify_021.json` 收口。最终工作树通过 429 项全量测试、Ruff、JavaScript、Skill、schema/trace、wheel 隔离安装、同 range Fireworks 样张与 localhost DOM 门禁；样张额外 SVG 只作为当前 HTML 的阅读附注，不进入 renderer、schema 或 Audit Graph。功能提交 `5e6b142b…` 已 push 至 `origin/codex/feat-audit-json-v0`，交付证据见 `exec_001.json`。Qoder 模型级 smoke 由用户后续手工验证；方案归档、tag、PyPI 发布和旧仓库处理未获授权，本轮不执行。
