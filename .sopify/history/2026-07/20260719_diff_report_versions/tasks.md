# 任务清单：通用 diff 与报告版本输出

归档目录：`.sopify/history/2026-07/20260719_diff_report_versions/`

## 1. Runtime

- [x] 1.1 复用现有 fingerprint/hash，实现新报告的 `diff_version` 写入以及 finalize 的 `diff_version / report_version` 返回。
  - 验收：正式 JSON 中只写 `diff_version`；`report_version` 精确对应最终 `audit.json` 原始字节。
- [x] 1.2 让 revise 在 copy、in-place、连续修订和 recovery 成功路径返回两个版本值。
  - 验收：新报告继承 `diff_version`；缺少该字段的 legacy schema `0.4` 报告返回 `null`，仍可修订。

## 2. Public contract and verification

- [x] 2.1 同步 `skills/evidentloop/SKILL.md`、宿主集成文档与数据模型说明。
  - 验收：通用契约不出现 Sopify 字段、目录或默认工作流；schema/prompt 保持不变，package 在 release checkpoint 更新为 `0.1.0a2`。
- [x] 2.2 增加最小定向测试并运行全量回归、`ruff` 与 `git diff --check`。
  - 验收：覆盖 finalize、legacy revise、copy/in-place、连续 revise 和 recovery；不扩张为版本框架测试矩阵。
