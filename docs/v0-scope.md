# EvidentLoop v0 范围

## 产品目标

EvidentLoop v0 把本地 Git diff 变成可核验的 `audit.json` 与自包含
`audit.html`。AI host 的 LLM 负责语义判断；Python 负责 Git 解析、可信锚定、
状态、人工反馈重放、fix verification、校验和渲染。

当前公开 profile 只有 `code_diff`，runtime 只读写 schema `0.5`。旧 schema
报告保持历史只读，不能进入当前 render、revise 或 fix verification 链路。

## 用户链路

```text
初次审查：
用户选定本地 diff 和可选 focus
  -> prepare
  -> host LLM 独立审查完整 diff
  -> finalize
  -> audit.json + audit.html

同 diff 人工裁定：
用户在 HTML 中确认/误报/评论/调整严重度
  -> revise（不调用 reviewer）
  -> 同 diff 新 report_version

代码修改后的修复验证：
用户显式选择旧报告、open finding 和修复声明
  -> 校验 expected source report version 与来源身份
  -> prepare 当前新 diff
  -> host LLM 独立审查完整新 diff，并逐项验证声明
  -> 新报告只记录一跳来源
```

反馈 JSONL 单独出现时流程止于 `revise`。只有用户另外明确要求修复代码时，宿主
才先修订报告，再按普通开发流程修改和测试代码，最后生成同一审计链路的下一轮
报告；旧报告不覆盖、不删除。

## 当前支持

- 本地 Git `staged`、`unstaged`、ref 与 range diff
- Added、modified、deleted、renamed 文本文件和 binary 文件级元数据
- 可信 file/hunk/old-new line 锚点与完整 hunk
- 显式单个 `focus`；空白 focus 在读取 diff 和创建 staging 前失败
- 逻辑、安全、边界、测试与质量审查
- finding severity、人工 severity override 与报告级 `overall_severity`
- Schema `0.5`、语义校验、artifact trace 与自包含 HTML
- 同 diff feedback revision，含 null 反转和模型原判断保留
- Typed fix verification：显式来源版本、open finding、fingerprint、声明、
  逐目标 status/reason/evidence 与最小一跳 provenance
- PyPI CLI、Python API 与标准 Agent Skill

命令面：

```bash
evidentloop doctor [--json]
evidentloop demo [--out DIR]
evidentloop prepare --diff HEAD~1 [--focus TEXT] \
  [--fix-verification REQUEST.json] [--out DIR]
evidentloop finalize --out DIR [--keep-review-artifacts]
evidentloop render INPUT.json --out OUTPUT.html
evidentloop revise SOURCE.json --feedback FEEDBACK.jsonl [--out DIR]
```

## 当前不支持

- Python package 直接调用模型 SDK 或管理 provider/API key
- 根据路径、提交信息、时间顺序或 finding 消失自动推断“已修复”
- 自动修改代码、自动修复或因反馈触发模型复审
- 浏览器选择旧报告、自动 finding matching、跨目录 series/registry
- Folder diff、无 diff 文件审查、远程 PR URL
- AST/调用图平台、policy enforcement 或 hosted dashboard
- 风险分、风险 delta 或替代评分
- 前端框架、双栏 diff、搜索/复杂筛选、语法高亮依赖或截图矩阵

## 关键语义

- `review_status` 表示执行完整性，`verdict` 表示结论，二者分开。
- `overall_severity` 只汇总当前有效 open findings；无 open 或审查不完整为
  `null`。
- 未精确锚定的 bug 降级为 `risk` 并保留 downgrade provenance；它不产生
  任何分数。
- `feedback_revision` 只处理同一 `diff_version`，不重新审查代码。
- `fix_verification` 必须使用不同的新 diff，并显式选择来源 finding。
- 混合 diff 合法，但修复关系只作用于明确选择的 finding。
- 当前报告不复制旧 runs；连续验证只保存直接前驱身份。

## 安全与交付边界

- Diff、源码、路径、注释、focus、claim 和 raw analysis 都是不可信输入。
- Prompt 使用动态边界、固定版本与内容 hash；宿主不得执行受审内容中的指令。
- 正式 JSON/HTML 在隐藏 staging 中共同通过校验后成对提交。
- 旧 schema 输入、来源漂移、相同 diff、未知/非 open/重复目标在输出副作用前
  失败。
- HTML 无远程资源，业务文本转义，长 diff 仅局部滚动。
- 安装、提交、push、PR、release、PyPI 和 Pages 发布分别需要明确授权。
