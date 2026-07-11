# 技术设计：change-audit v0 code-diff 一期闭环

## 设计原则

- `audit.json` 是唯一机器真相源。
- 宿主 LLM 负责语义判断，Python 负责确定性装配、校验和渲染。
- ReviewPack、prompt、raw analysis 和 ReviewResult 是内部传输，不是用户产品契约。
- `render` 纯消费完整 `audit.json`。
- 默认路径不调用模型 SDK、不读取 API key、不自动修改代码。
- `change_audit.review` 保留 artifact-general 演进方向；公开 audit 能力按 profile 成熟度放行。
- `audit.json` 与 `audit.html` 先在 staging 中完成全部校验，再作为正式产物对发布。
- 一期采用本地 single-writer：同一最终目标同一时刻只由一个 change-audit 流程写入，不提供原生 no-replace 或对抗性竞态保证。

## 总体架构

![change-audit review architecture](../../../docs/assets/change-audit-architecture.svg)

对应 PNG：[`change-audit-architecture.png`](../../../docs/assets/change-audit-architecture.png)

```text
User
  -> AI host + change-audit Skill
  -> prepare
     -> audit/.<slug>.change-audit-staging/.run/
        -> audit-skeleton.json
        -> review-pack.json
        -> hunk-index.json
        -> prompt.md
  -> isolated host LLM
     -> staging/.run/raw-analysis.md
  -> finalize
     -> ingest -> ReviewResult
     -> Audit Graph adapter
     -> schema + reference + anchor validation
     -> staging/audit.json
     -> render + trace validation
     -> staging/audit.html
     -> single same-filesystem directory rename -> final audit directory
  -> human decision -> audit-feedback.jsonl
```

详细时序见 [AI host review flow](../../../docs/assets/change-audit-review-flow.svg)。

## 目标目录

```text
pyproject.toml
change_audit/
  __init__.py
  __main__.py
  api.py
  cli.py
  validation.py

  review/
    pack.py
    ingest.py
    normalizer.py
    adjudicator.py
    budget.py
    config.py
    schema.py
    reviewer.py
    core/prompt.py

  adapters/
    gitdiff.py

  audit/
    adapter.py
    finalize.py

  schemas/
    audit-v0.schema.json

  renderers/
    html.py
    hunk.py
    templates/audit.html.j2
    static/audit.css
    static/audit.js

integrations/
  agent-skill/change-audit/SKILL.md

tests/
  review/
  test_schema.py
  test_validation.py
  test_renderer.py
  test_adapter.py
  test_finalize.py
  test_package_resources.py
```

## 命令与 API 边界

一期有三个 Python 命令：

```bash
python -m change_audit prepare --diff HEAD~1 [--out DIR]
python -m change_audit finalize --out DIR [--keep-review-artifacts]
python -m change_audit render INPUT_JSON --out OUTPUT_HTML
```

- `prepare`：读取 Git diff，选择尚不存在的最终目录，并在同父目录创建隐藏 staging workspace 与运行上下文。
- `finalize`：读取宿主审查输出，执行 ingest、adapter、校验、自动渲染和正式产物对发布。
- `render`：从完整 JSON 单独重建 HTML。

`review` 不是 Python 命令。它是 Skill 暴露给用户的自然语言动作。

公开 Python API 与命令同构：

```python
prepare_local_diff(repo_path, diff_spec, output_dir=None)
finalize_review(output_dir, keep_review_artifacts=False)
render_audit_file(input_path, output_path)
```

Wave 1 只实现 `render_audit_file()` 和 `render`。另外两个签名先作为设计契约记录，Wave 2 才落代码，不创建空壳实现。

`prepare_local_diff()` 成功返回结构化 locator，至少包含 `run_id`、`final_dir` 和 `staging_dir`。CLI 将该 locator 作为唯一 stdout JSON，诊断写 stderr；Skill 原样使用 locator，不自行复刻 slug、冲突后缀或 staging 命名规则。`finalize --out` 只接受 locator 的 `final_dir`，并验证 staging、骨架与 raw analysis 属于同一 `run_id`。

## 隐藏 staging 与运行上下文

目标最终目录必须不存在。`prepare` 在同一父目录以 exclusive create 创建隐藏 sibling workspace：

```text
audit/.<slug>.change-audit-staging/
  .run/
  audit.json               # finalize 候选，prepare 时不存在
  audit.html               # finalize 候选，prepare 时不存在
```

`.run/` 内容：

| 文件 | 写入者 | 消费者 | 作用 |
|---|---|---|---|
| `audit-skeleton.json` | prepare | finalize | run/change/file 骨架；不是用户最终产物 |
| `review-pack.json` | prepare | finalize | CrossReview ReviewPack |
| `hunk-index.json` | prepare | finalize | 可信 hunk ID、路径、old/new 范围和完整 snippet |
| `prompt.md` | prepare | Skill / host LLM | 已封装的不可信 diff 与审查指令 |
| `raw-analysis.md` | Skill | finalize | 宿主 LLM 原始分析 |
| `review-result.json` | finalize | 诊断 | 仅失败或显式保留时物化 |

约束：

- staging leaf 必须由本轮 exclusive create；prepare 与提交前都检查最终目标 leaf，任何已有 entry（包括悬空符号链接）都拒绝。一期不递归检查父目录中的符号链接。
- POSIX 平台尽力将 staging 目录设为 `0700`、中间文件设为 `0600`；不支持这些权限位的平台正常运行，权限模式不作为跨平台退出门禁。
- staging 内部文件使用临时文件加同目录原子替换；独立 `render --out` 也以该方式替换单个 HTML，失败时保留旧 HTML 且不修改输入 JSON。
- finalize 成功提交前默认删除 staging 内 `.run/`；`--keep-review-artifacts` 时保留，并随目录 rename 进入最终目录。
- 提交前失败时最终目录保持不存在，staging 保留并报告路径。
- `.run/` 不是稳定外部 API；稳定诊断字段由内部版本号保护。
- staging 根目录候选 JSON/HTML 不得被 Skill 当作正式产物展示。

## ReviewResult 到 Audit Graph

Adapter 不做简单字段复制，而是完成以下工作：

1. 把 ReviewResult finding 映射到四类 audit category。
2. 用 `hunk-index.json` 解析可信 `hunk_id`、完整 hunk 和 highlight lines。
3. 生成全局唯一 node ID、edge 和 fingerprint。
4. 生成 evidence / fix 关系。
5. 映射 review status 和 verdict；覆盖诊断只写入 namespaced extensions。
6. 聚合已评分 finding，并记录未计分 finding。

### Category 映射

| Review category 族 | Audit category |
|---|---|
| `bug`, `logic_error`, `semantic_equivalence`, `correctness` | `bug`，但必须精确锚定 |
| `security`, `performance`, `missing_validation`, `error_handling` | `risk` |
| `possible_bug` | `risk` |
| `quality`, `maintainability`, `missing_test`, `style`, `suggestion`, `documentation`, `testing` | `quality` |
| `scope`, `spec_mismatch` | `scope` |
| 未知值 | `quality`，原值写入 `extensions.change_audit.original_category` |

精确 bug 无法从可信 hunk index 解析时：

- category 降级为 `risk`；
- 写入 `extensions.change_audit.downgraded_from = "bug"`；
- 写入稳定降级原因；
- HTML 显示“语义发现，位置未精确锚定且未计分”；
- 不进入数字风险评分。

### Hunk 解析

ReviewResult 的 `diff_hunk` 可能只有 `@@ ... @@` header，不能直接作为展示 hunk。Adapter 按以下优先级反查：

1. file + line + header；
2. file + line；
3. file + 唯一匹配 header。

成功后，finding 写入可信 `hunk_id`、完整 `hunk`、`start_line`、`end_line`、`line_side` 和 `highlight_lines`。无法解析时按 category 精度策略降级，不从 LLM 文本复制伪造代码。

## 状态、结论与覆盖

`summary.review_status` 与 `summary.verdict` 各自只有一个职责：

| 场景 | review_status | verdict | risk_score |
|---|---|---|---|
| 未执行审查 | `not_reviewed` | `inconclusive` | `null` |
| 完整、无未解决 finding 且 core 认为上下文充分 | `complete` | `pass_candidate` | 0 |
| 完整、无未解决 finding 但 core 认为上下文不足 | `complete` | `inconclusive` | `null` |
| 完整且有未解决、已锚定 finding | `complete` | `concerns` | 0–100 |
| 只有未锚定降级风险 | `complete` | `needs_human_triage` | `null` |
| 部分审查（finding 可有可无） | `partial` | `inconclusive` | `null` |
| 审查失败 | `failed` | `inconclusive` | `null` |

ReviewResult 的 intent coverage、files reviewed 和 pack completeness 含义不同，只作为 `summary.extensions.change_audit.review_diagnostics` 中的诊断信息保存。HTML hero 必须同时展示 status 和 verdict，不能用一个字段模拟另一个字段。

## 风险评分

- 范围固定为 0–100 或 `null`。
- 只有当前未解决且通过分类锚点策略的 finding 进入评分；bug 需要精确 hunk，risk/quality/scope 可使用可信 file-only 锚点。
- `unscored_finding_count` 记录因锚点降级而排除的未解决 finding 数量；不会因为整体状态是 partial/failed 自动把全部 finding 计入。
- 实现期可以使用集中配置的临时 severity 权重并封顶 100。
- 权重不是当前结构契约；Wave 2 使用三类 dogfood 校准后再冻结并写入测试。
- 手工样张中的现有分数是产品形态数据，不是未来算法的金标准。

## Renderer 行为

Renderer 只读取完整 `audit.json`：

- `complete + pass_candidate + 0 open findings`：仅在 core advisory verdict 同意候选通过时显示“未发现未解决问题”；若完整输出仍因上下文不足为 `inconclusive`，hero 明示结论不充分且不渲染空问题模块。
- `not_reviewed`、`partial`、`failed`：hero 明示状态，不得显示为干净审查。
- 只有降级风险：渲染风险 section，显示未定位标签，风险分显示“无法可靠评分”。
- 有 finding：展示 category、severity、可信 hunk 片段、evidence 和反馈控件；只有图中存在独立、可靠的 fix 节点时才展示修复建议。`audit.json` 保留从可信索引复制的完整 hunk，HTML 使用接近 diff2html 的双行号 table 仅渲染覆盖命中行的有界上下文，明确区分 context/add/delete、突出命中行、显式标记省略行并保留 `data-*` 回链，禁止用普通 `<pre>` 代替可信 diff 证据。
- 报告主标题使用仓库友好名，精确 diff range 保留在 `source.ref`；完整性门禁通过后，renderer 展示 reviewer 的 `Overall Assessment` 作为转义后的 run 语义摘要，change 卡片展示 Python 生成的文件数与增删行统计。该语义摘要不参与 status、verdict 或风险评分。
- code-diff 一期正式报告以简体中文为主要用户语言。product prompt 保持 Section/field 标签和枚举协议不变，仅要求 finding/observation/overall 的语义正文使用简体中文；prepare 冻结 prompt source/version/hash，finalize 校验后复用该 provenance，避免跨进程版本漂移。
- 没有结构化 claim 时只显示顶对齐的紧凑弱提示，不拉伸到文件列表高度。hunk table 默认固定布局并对代码自动换行，使有界片段在常见桌面和移动视口无需横向滚动即可完整阅读；滚动仍作为极端内容兜底，命中行使用独立于 add/delete 背景的高对比标记和中文图例。
- ReviewResult 当前只提供问题摘要与原因，没有独立修复建议。adapter 必须生成 host review evidence，但不得把 Why 复制为 fix；只有未来获得独立、可靠、可校验的修复建议时才生成 `requires_fix`。任何带 `extensions.change_audit.unscored=true` 的 finding 都在 HTML 明示未精确定位。
- reviewer 使用不含 `GIT binary patch` 的文本 diff，二进制文件只进入 file metadata；这不丢失一期承诺的证据。adapter 保留 core advisory verdict：输出契约完整但 pack completeness 不足时允许 `complete + inconclusive + risk_score=null`，HTML 必须解释 complete 不等于覆盖充分。
- 可选字段缺失时降级；结构、引用或回链断裂时，完整 finalize 阻止整对提交，独立 `render` 则保留旧 HTML 不变。

## 正式产物对发布

finalize 不先创建最终目录中的 `audit.json` 再尝试 render。正确顺序：

1. prepare 已在最终目录同父目录创建隐藏 staging workspace；最终目录仍不存在。
2. finalize 在 staging 根目录写候选 `audit.json`。
3. 对候选 JSON 执行 schema、引用、锚点、状态和计数校验。
4. 从候选 JSON 渲染候选 `audit.html`，再执行 HTML `data-*` 回链、run/graph identity、XSS 和完整性校验。
5. 两个候选均通过后，按 keep 策略处理 `.run/`，再次检查最终目标 leaf 不存在，再用一次同文件系统目录 rename 把 staging 提交为最终目录。
6. 对 prepare 已接受的新目标，任一提交前失败时最终目录保持不存在，staging 留作诊断；检测到已有目标 leaf（包括符号链接）或 rename 失败时停止，不主动覆盖，也不把旧目标当作本轮成功。

同一文件系统的单次目录 rename 是产物对的提交点，`run_id` 保证跨进程材料属于同一次运行。实现必须保证“成功状态只对应完整产物对”，不得把 staging 文件或旧报告当作成功。本约束基于本地 single-writer，不承诺处理两个进程在检查与 rename 之间对抗性争抢同一目标；原生 no-replace 与更强并发防护留待后续加固。

## Prompt Injection 边界

- prompt 使用每次运行生成的不可预测边界标记包裹不可信 diff，不能依赖源码可提前闭合的固定围栏。
- Skill 和宿主不得执行 diff、源码注释或 raw analysis 中建议的命令。
- LLM 只能返回审查文本，不直接写 `audit.json`。
- finalize 只有在输出包含完整 findings section（允许显式零 finding）和 Overall Assessment 时才认定 `complete`；截断、缺段或无法证明完成时映射为 `partial` 或 `failed`，不得把解析到的空列表推断为干净审查。
- 测试 fixture 包含“忽略之前指令”“运行 shell”“泄露环境变量”等恶意源码文本。
- Jinja2 对所有业务文本 autoescape；可信内联 CSS/JS 只来自 package resources。

## 失败产物边界

- 宿主拒绝、明确审查失败或可归一化的 ingest 失败：finalize 可从可信骨架写出 `review_status = failed` 的 `audit.json` 与 `audit.html`，让用户看见真实失败状态。
- schema、安全、路径/leaf、`run_id`、render、trace 或目录 rename 等硬失败：返回非零；新目标保持不存在并保留 staging 诊断，已有目标不得作为本轮成功报告。
- 任何失败路径都不得复用旧产物或宣称审计完成。

## Artifact-general 长期边界

长期分成两层：

- `change_audit.review`：artifact-general 隔离审查内核。plan、design、analysis、review-result、agent output 等类型可以逐步增加 ReviewPack profile、prompt 和 ReviewResult eval。
- `change_audit.audit` + renderer：正式产品层。只有同时具备 adapter、可信 anchor、eval baseline 和 renderer profile 的 artifact 类型，才承诺生成 `audit.json` 与 `audit.html`。

一期只实现 `code_diff` profile。实验性非 diff 类型可以先停在内部 ReviewResult 或宿主摘要，不得包装成已完成的正式 audit。

当前 Audit Graph 的 `artifact` 节点表示派生正式产物，不复用为“被审查输入”。第二种真实 artifact profile 进入设计时，再通过独立 ADR 和 schema 版本引入 review target、section/claim/JSON Pointer/message 等 anchor；不在 `0.2` 中预塞大量 nullable 字段。

未来 renderer 保持共同外壳：status、verdict、summary、findings、evidence、fix 和 human decision 一致；定位模块按 profile 切换，例如 code diff 使用 hunk，plan/design 使用 section/claim/excerpt。没有成熟 renderer profile 时不生成伪完整 HTML。

## CrossReview 迁移边界

- Wave 0A 记录真实 commit、PyPI 版本、pytest collection、prompt 版本和 eval 基线。
- Wave 0B 只建立 import 所需最小包壳并迁移代码、测试、prompt template 与 harness，不引入 adapter 行为。
- 真实 eval fixture 继续留在隔离数据源；main 只保留 harness 和 synthetic fixtures。
- 旧 `crossreview` CLI 不进入新 distribution。
- provider-backed reviewer 可作为可选 extra 保留等价性，但默认 Skill 与命令不调用它。
- publish workflow 只设计不启用；旧仓库和 PyPI 包本期不删除、不 yank。

## 验证设计

- Migration：固定输入的 ReviewResult 前后等价，原测试和 eval gate 不退化。
- Schema：严格核心、extensions、review status、verdict、nullable score 和 unscored count。
- Anchor：多个 hunk、删除行、rename、header-only、file-only、未知路径和伪造 header。
- Adapter：已知 category、未知 category、bug 降级、unscored count、状态映射。
- Security：prompt injection、XSS、目标/staging leaf 拒绝和失败保留；POSIX 权限仅做 best-effort 验证，不作为跨平台门禁。
- Renderer：完整样张、无 finding、只有降级风险、partial、failed 和 trace validation。
- Publication：JSON 校验失败、render 失败、trace 失败、`run_id` 不一致、已有目标 leaf 和 rename 失败均不得产生可宣称成功的半套正式产物；对抗性竞态与进程中断故障注入延后。
- Package：wheel 隔离安装读取 schema、template、CSS、JavaScript 和 prompt resource。
- Host：中文/英文触发、安装授权、拒绝安装、命令失败、缺产物、Codex 和 Qoder。

## 文档与知识同步

方案确认时同步 README、v0 scope、data model、AI host integration、样张说明、project 和 blueprint。历史归档保持原决策，不回写。实现期只更新实际状态和验证结果。
