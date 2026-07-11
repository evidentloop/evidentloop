# Fireworks Tech Graph 真实 dogfood

这份目录以 `change-audit` 在实现完成后生成的真实能力样张为核心。输入与实现前模拟基线完全相同，报告没有复制基线的 finding、claim 或修复建议；它从全新 staging 重新执行了 `prepare → 隔离宿主审查 → finalize`。

真实链路完成后，按本样张审计需要，另用 Fireworks Tech Graph Skill 从同一 diff 提炼了一张技术架构 SVG，并以内联 data URI 加入当前 `audit.html` 的“变更摘要与审计结论”区。这个阅读附注没有修改 `audit.json`、finding、评分、renderer、schema 或正式生成链路。

## 固定输入

- 源仓库：`fireworks-tech-graph`
- Git diff：`d5ef26deac6b1ed37ee9b89b52dddb1bcaac6c24..9a64e5a926d430a421a71b5cf433b0553876db28`
- 变更规模：21 个文件，`+914/-281`，其中 5 个二进制文件
- 可信索引：52 个 hunk
- Reviewer prompt：`product/v0.2`
- Prompt SHA-256：`cf61820cc2e5e26c2489f12a6ba6587cc4c0ae4a79fc66a622f8998f84b4279c`
- Run：`run-d7f8986d1ab24a04a6078f1afca17d1e`

文本 reviewer payload 不包含 `GIT binary patch`，仍保留 5 个二进制文件的路径和 Git binary 占位。视觉像素差异不在这次文本审查的结论范围内。

## 真实结果

- 状态：`complete + concerns`
- 已计分风险分：100（按冻结权重计算并封顶）
- Finding：7 条，全部精确锚定到真实新增行
- 未计分 finding：0
- Fix：0；ReviewResult 没有独立修复建议，不能把问题原因冒充修复动作
- 语义正文：简体中文
- Summary claim：未生成；HTML 使用紧凑弱提示，不伪造声明审计
- 样张图解：1 张；把新增校验链路和 7 条 finding 收敛为 4 个审计关注面，不参与评分

审查者第一次返回时语义内容完整，但 Section 标题和 `Where` 格式不满足机器协议。没有人工改写结论，而是让同一隔离审查者只修正格式并原样重发；之后才进入 finalize。最终 7 个位置均由可信 hunk index 验证为新增行。

## 产物

- [`audit.json`](./audit.json)：机器真相源，保存完整可信 hunk、prompt provenance、状态、评分和关系。
- [`audit.html`](./audit.html)：面向阅读的自包含报告，只展示命中附近的有界可信片段；当前文件额外内联一张样张专用架构图。
- [`fireworks-diff-architecture.svg`](./fireworks-diff-architecture.svg)：同一 diff 的校验架构与审计关注面；不属于 Audit Graph。
- [`baseline-comparison.md`](./baseline-comparison.md)：实现前模拟基线、失败纠偏轮次和最终真实报告的差异。

当前样张文件 SHA-256：

```text
ee52e12329a25fcee6ce6bee6c82725f8d64c8e1ae38af07fed457ff6bcad0b8  audit.json
d527cc76f384b2cf9a38cd0cd95f111f05a116486e1226c94cb0c2e083357f1d  audit.html
122e5438db087e7d34dde76e406410c0b51133e4f556e0cf5498fa98f5284e2b  fireworks-diff-architecture.svg
```

其中，`finalize` 原始生成的 HTML SHA-256 为 `3a4b279374e930e69d01ea0056bc82bbc4883465185d78058a25eb505f91da65`；当前哈希变化只来自样张图解层。内联 SVG 解码后与独立 SVG 字节完全一致，现有 schema 与 HTML trace 仍为 0 issue。

HTML 在应用内浏览器中通过 localhost 实测：1280px 和 375px 都没有页面级横向溢出；7 个 hunk 无横向或纵向内部滚动，代码按行换行完整显示；文件列表、审查依据和高级反馈默认折叠。架构图在 1280px 下完整自适应且无滚动；375px 下保留图卡内部横向查看，避免把 1200px 图缩小到不可读。`file://` 自动化被宿主安全策略拒绝不属于页面故障，因此实时 DOM 门禁统一通过 `http://127.0.0.1` 执行。

## 重生成

以下命令只重建 renderer 的原始 HTML，不重新调用审查者，也不会修改 `audit.json`；它会移除当前样张专用架构图，需要保留图解时不要覆盖本文件：

```bash
python -m change_audit render \
  docs/examples/dogfood-fireworks-tech-graph/audit.json \
  --out docs/examples/dogfood-fireworks-tech-graph/audit.html
```

要重新审查，必须换一个尚不存在的输出目录，从 `prepare` 开始；不得覆盖本目录后把旧产物当作新运行。
