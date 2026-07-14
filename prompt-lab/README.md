# Prompt Lab

Prompt Lab 是 EvidentLoop 的仓库级开发工具，用于验证 reviewer prompt 质量。它只做两件事：

1. 使用产品唯一的 canonical prompt 渲染已保存的 ReviewPack。
2. 离线聚合已经落盘的 fixture、ReviewResult 与人工 adjudication。

Prompt Lab 是离线开发工具，不调用模型，也不进入正式 wheel。

先在仓库 checkout 中安装开发依赖：

```bash
python -m pip install -e '.[dev]'
```

## 单一 prompt 来源

canonical prompt 位于：

```text
evidentloop/review/core/reviewer-prompt.md
```

当前版本为 `product/v0.5`。`prompt-lab/run.py` 与产品 `prepare` 读取同一文件；Prompt Lab 不维护第二份实验模板，避免 prompt 版本和协议分叉。

## 渲染 prompt

在仓库根目录执行：

```bash
python prompt-lab/run.py \
  prompt-lab/cases/001-auth-refresh
```

case 目录至少包含一个 `pack.json`：

```json
{
  "artifact_type": "code_diff",
  "diff": "<unified diff text>",
  "changed_files": ["src/auth/token.ts", "src/auth/types.ts"],
  "intent": "修复 token refresh 过期判断",
  "focus": ["auth"],
  "context_files": [],
  "evidence": []
}
```

命令会生成 `rendered-prompt.md`。将其交给 fresh host LLM session 后，响应应另存为 case 证据；Prompt Lab 本身不发起模型请求。

`run.py` 的 raw response 是手工实验记录，不会自动变成 eval 输入。`eval.py` 只重放已经物化的 `review-result.json`。要建立真实 fixture，应走正式 `prepare → host review → finalize --keep-review-artifacts` 主链，再从成功报告目录的 `.run/review-result.json` 取得同一运行的确定性结果，并保留 prompt provenance；不要把 raw Markdown 直接交给 eval，也不要在 Prompt Lab 复制一套 ingest 逻辑。

## 离线 fixture 评估

每个 eval fixture 目录包含：

```text
fixture.yaml
pack.json
review-result.json
manual-findings.yaml
auto-adjudications.yaml
```

运行 release gate 聚合：

```bash
python prompt-lab/eval.py \
  --fixtures /path/to/fixtures \
  --output /tmp/evidentloop-eval.json
```

只查看回归指标、不计算 blocking release gate：

```bash
python prompt-lab/eval.py \
  --fixtures /path/to/fixtures \
  --mode regression
```

eval 只读取保存的文件，不调用 reviewer backend。真实 fixture 与其 README 不纳入当前 `main`。

## manual-findings.yaml 格式

手工 baseline 格式如下：

```yaml
fixture_id: "001-auth-refresh"
source: manual_fresh_session
reviewer_model: "claude-sonnet-4-20250514"
reviewed_at: "2026-04-20T16:00:00+08:00"
context_items:
  - type: diff
    path_or_desc: "src/auth/token.ts"
    required: true
    covered_by_pack: true
findings:
  - id: "mf-001"
    summary: "Token expiry off-by-one"
    file: "src/auth/token.ts"
    severity_estimate: medium
```

## 评估口径

Prompt Lab 默认评估单次审查（single-pass review）的原始质量。后续独立复核可以验证 finding、剔除幻觉或补充遗漏，但不得把复核增益记到 reviewer prompt 的 first-pass 指标中。

人工 baseline 是 recall 的分母，必须遵守：

1. 先落盘 baseline，再执行 reviewer。
2. 编写 baseline 的人或 session 不得接触当次 reviewer 输出。
3. 事后补写 baseline 时，必须在汇总中标注 `baseline: post-reviewer`。
4. 每批新增 fixture 至少包含一个 clean diff，避免样本只覆盖 bug-heavy 变更。

release-gate 与 regression 报告都按 external 与 self-hosting 两个 pool 分开汇总。真实发布判断以 external pool 为主要证据，self-hosting 只作为补充。
