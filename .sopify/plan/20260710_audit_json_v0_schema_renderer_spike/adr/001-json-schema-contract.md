# ADR-001：以 JSON Schema 作为 audit.json 唯一结构契约

## 状态

已采纳

## 日期

2026-07-10

## 上下文

`audit.json` 会被 prepare/finalize、HTML renderer、反馈工具和未来外部消费者共同使用。若同时维护 Markdown、Python model 和外部 schema，字段与枚举会形成多个可漂移的权威来源。

JSON Schema 可以表达对象结构、必选字段、枚举、类型和未知字段策略，但无法完整表达跨数组 ID、edge 端点、claim 与 HTML 回链。

## 决策

- 使用 JSON Schema 2020-12 作为 `audit.json` 唯一结构契约。
- Python 使用 `jsonschema` 校验结构，不再声明一份等价的 Pydantic 模型。
- Python 语义校验只负责 ID、edge、claim、hunk anchor 和渲染回链。
- 核心对象使用 `additionalProperties: false`；扩展数据进入 namespaced `extensions`。
- ReviewPack 与 ReviewResult 是内部 review 契约，独立版本化，不与 audit schema 版本混用。
- Schema 在真实宿主审查 dogfood 通过前保持 `0.2-alpha`；Wave 2 的精确语义 bug、显式干净 diff、partial review 和未锚定降级流水线均通过后，code-diff profile 已冻结为 `0.2`。
- 本 ADR 的 `0.2` 当前只适用于首个 `code_diff` audit profile；未来 artifact profile 按 ADR-004 单独建立版本化 schema 与 anchor，不把 `0.2` 误作万能契约。

## 理由

该方案让对外结构保持语言无关，同时把 Python 专属逻辑限制在 JSON Schema 不擅长的全局关系校验，减少双重真相源。

## 替代方案

- Pydantic 作为权威：拒绝，因为外部消费者仍需要独立 schema。
- 手写 Python 校验：拒绝，因为难以被非 Python 工具复用。
- 完全宽松对象：拒绝，因为拼错字段会静默进入正式产物。

## 影响

- 发布包必须携带 schema。
- 所有 schema 变更必须同步 fixture 和文档。
- ReviewResult 到 Audit Graph 的 adapter 必须在写入前通过结构与语义校验。
- `0.2` 冻结后，破坏性结构变更必须升级 schema 版本。
