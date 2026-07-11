# 同源基线对比

三份材料使用完全相同的 Fireworks Git diff：

```text
d5ef26deac6b1ed37ee9b89b52dddb1bcaac6c24..9a64e5a926d430a421a71b5cf433b0553876db28
```

实现前基线只用于定义产品阅读形态；最终报告必须来自真实链路，不能复刻基线结论。

| 项目 | 实现前模拟基线 | 首次真实纠偏（失败取证） | 最终真实报告 |
|---|---:|---:|---:|
| 生成方式 | 手工设计链模拟 | `prepare/finalize` | 全新 `prepare/隔离审查/finalize` |
| review status | partial | complete | complete |
| verdict | inconclusive | concerns | concerns |
| risk score | null | 76 | 100（封顶） |
| findings | 4 | 7 | 7 |
| 精确可信 hunk | 0 | 5 | 7 |
| 未计分 findings | 0 | 2 | 0 |
| fixes | 4 个手工建议 | 6 个由 Why 误复制的伪 fix | 0 |
| structured claims | 7 个手工 claim | 0 | 0 |
| 语义正文 | 中文 | 英文 | 中文 |
| prompt | 无正式运行 | `product/v0.1`，约 2.54 MB | `product/v0.2`，83,919 bytes |
| binary payload | 模拟说明 | 含 `GIT binary patch` | 不含 payload，保留 5 个文件元数据 |
| JSON bytes | 22,539 | 84,916 | 139,868 |
| HTML bytes（生成链路原始输出） | 45,591 | 112,706 | 122,303 |

## 为什么最终 JSON 更大

`audit.json` 是机器真相源。最终 7 条 finding 都保存完整可信 hunk，其中 6 条定位到新增的 484 行 validator 文件，因此 JSON 体积增加是完整证据的直接结果。HTML 没有重复展开 484 行：6 张卡片各显示命中附近 17 行，另一张显示完整 40 行 shell hunk，并明确标出省略数量。

## 结论变化

- 模拟基线与最终报告都识别到 legend 几何启发式风险；最终报告由隔离审查者独立重新发现，并给出 `scripts/validate_svg.py:415` 的真实新增行锚点。
- 两份报告也都识别到静态 PNG 导出失败仍打印成功并增加 `PASSED`；最终报告独立定位到 `scripts/test-all-styles.sh:155`，没有复用基线文字或手工 fix。
- 其余五条最终 finding（`data-graph-role="node"`、CSS marker、圆弧、multi-subpath、skew transform）不在模拟基线中，来自本轮真实审查链路。
- 最终报告不生成结构化 claim，也不生成 fix。这是当前 ReviewResult 能力边界，不应为接近手工基线而伪造。
- `review_status=complete` 只表示输出满足结构契约；报告仍保留 `intent_coverage=partial` 和 `pack_completeness=0.65`，HTML 明示完整输出不等于覆盖充分。

## 样张专用图解层

最终真实链路与独立复审完成后，当前 `audit.html` 按人工审计需要额外内联了 `fireworks-diff-architecture.svg`。图只概括同一 diff 的校验架构与 4 个审计关注面，不改变 `audit.json`、7 条 finding、评分或上表中的生成链路原始输出。

当前带图解的 HTML 为 136,310 bytes；内联 SVG 解码后与 9,424 bytes 的独立 SVG 完全一致。该附注是样张展示层，不纳入 renderer 或 schema。

## 可核对哈希

实现前模拟基线：

```text
f253d2b2cf53342fe4112e44ce58bf95e6d8329a9d820eaed64737c571d0cd13  audit.json
bf3c371d7eeb4fe0e99a1393ac075f49ffbe351b658c78cd2d1d61f3dfc669ec  audit.html
```

首次真实纠偏失败取证：

```text
d30f6c1c73d4bc2a7f70504ae52f45d3de75c478593f2cb92e81529d07309f65  audit.json
74d8b04cafbcdfda7884abcdd9753f97b218f34626b1e2ffd86c1193b877dea9  audit.html
```

最终真实报告：

```text
ee52e12329a25fcee6ce6bee6c82725f8d64c8e1ae38af07fed457ff6bcad0b8  audit.json
3a4b279374e930e69d01ea0056bc82bbc4883465185d78058a25eb505f91da65  audit.html
```

当前带样张图解的阅读文件：

```text
d527cc76f384b2cf9a38cd0cd95f111f05a116486e1226c94cb0c2e083357f1d  audit.html
122e5438db087e7d34dde76e406410c0b51133e4f556e0cf5498fa98f5284e2b  fireworks-diff-architecture.svg
```
