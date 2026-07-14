# Fireworks Tech Graph `product/v0.3` 历史对比证据

> 本目录由原 `change-audit` 身份和 public schema `0.2` 生成。`audit.json` 与 `audit.html` 保留原始 provenance 和文件字节，只作为身份迁移前的历史证据，不作为 EvidentLoop schema `0.3` 的 renderer fixture。

本目录保存 Wave 5 单产品收口后的真实 dogfood。它与[保留的 v0.2 样张](../dogfood-fireworks-tech-graph/)使用完全相同的 Git diff，但从全新 staging 独立执行：

```text
d5ef26deac6b1ed37ee9b89b52dddb1bcaac6c24..9a64e5a926d430a421a71b5cf433b0553876db28
```

正式链路为 `prepare → 隔离宿主审查 → finalize`。没有复用旧 raw analysis，没有手改 `audit.json` / `audit.html`，也没有向 HTML 注入额外 SVG。旧目录保持字节级不变。

## 本次结果

- Run：`run-842aeae6dc0b48b88ab95b38097997a0`
- Reviewer prompt：`product/v0.3`
- Prompt SHA-256：`0400ed0b961edee4cea64cd5746ee411ccfc0e17511a53dc8c9b8e9471c558b7`
- 输入：21 个文件、52 个 hunk、`+914/-281`，其中 5 个二进制文件
- 状态：`complete + concerns`
- 风险分：100
- Finding：7 条，全部精确锚定真实新增行
- 未计分 finding：0
- Fix：0
- Schema / HTML trace：通过
- Localhost DOM：1280px 与 375px 均无页面级横向溢出，7 个 hunk 均无内部横向或纵向滚动

Reviewer 首次返回的语义内容完整，但 Section 标题和 `Where` 形式不满足机器协议。同一隔离 Reviewer 仅做格式重发，7 条 finding 和总体结论未改写；随后才执行 finalize。

## 与保留样张对比

| 项目 | 保留的 v0.2 样张 | 本目录 v0.3 证据 |
|---|---:|---:|
| prompt | `product/v0.2` | `product/v0.3` |
| review status | complete | complete |
| verdict | concerns | concerns |
| risk score | 100 | 100 |
| findings | 7 | 7 |
| 精确修改行锚点 | 7 | 7 |
| 未计分 findings | 0 | 0 |
| fixes | 0 | 0 |
| 原生 JSON bytes | 139,868 | 157,729 |
| 原生 HTML bytes | 122,303 | 114,819 |

两次隔离审查独立识别出 6 个共同问题；v0.2 另外识别到 shell 静态导出失败仍计为通过，v0.3 另外识别到圆/椭圆外接矩形碰撞误报。prompt 协议正文未变化，因此这组差异只证明真实模型审查存在运行间波动，不用于宣称 v0.3 提升了 finding 能力。

## 产物与哈希

- [`audit.json`](./audit.json)：机器真相源。
- [`audit.html`](./audit.html)：finalize 原生生成的自包含中文报告。

```text
dbf0ea2ede6e3094d5fd1910c3646f4bca4868aae1d62ef179533be474fbc374  audit.json
e9a70b56deaeac701b919323c7495b8a7aa39693c7b775bac20291ec4701a69c  audit.html
```

这些产物用于本地前后对比，不替代产品契约，也不代表审查者发现了该范围内的全部缺陷。
