---
title: 通用 diff 与报告版本输出
plan_id: 20260719_diff_report_versions
status: completed
lifecycle_state: completed
level: standard
created: 2026-07-19
updated: 2026-07-19
archive_ready: true
knowledge_sync:
  project: review
  background: skip
  design: review
  tasks: review
---

# 通用 diff 与报告版本输出

## Plan Snapshot

- **Goal**: 让所有 EvidentLoop 消费者从正式 finalize/revise 结果中取得稳定的 `diff_version` 与 `report_version`。
- **Status**: 最小实现、公共文档收口和 `0.1.0a2` 候选验证已完成。
- **Next**: 随发布候选提交归档，随后执行已授权的 PR、tag、PyPI 与 GitHub Release 发布链路。
- **Task**: 4/4。

评分:
- 方案质量: 9/10
- 落地就绪: 9/10

评分理由:
- 优点: 直接复用现有 diff fingerprint 与正式 JSON 字节哈希，不引入新 schema 或集成层。
- 扣分: 公开发布结果仍需由 GitHub Actions、Pages 与 PyPI 实际验证。

## Context / Why

EvidentLoop 已能生成和修订可验证的 `audit.json + audit.html`，但消费者只能自行理解内部 `artifact_fingerprint`，也无法从结构化结果直接取得当前正式报告的确定版本。Sopify 是首个需要这两个值的消费者，但能力本身必须保持产品通用。

## Scope

- 新 finalize 报告在 `audit.json.extensions.evidentloop.diff_version` 保存本次实际 Git diff 的版本。
- `finalize` 与 `revise` 的结构化结果返回 `diff_version / report_version`。
- revise 保留来源报告的 `diff_version`；旧 schema `0.4` 报告缺失时返回 `diff_version: null`。
- 同步公共 Skill、宿主集成文档和数据模型说明。
- 覆盖 finalize、copy、in-place、连续 revise、legacy 与 recovery 主路径。

## Approach

- `diff_version` 直接在现有 `artifact_fingerprint` 前加算法前缀，不重新读取或重算 Git diff。
- `report_version` 对正式 `audit.json` 原始字节计算；它不写回自身，只从 finalize/revise 结果返回。
- 增加一个内部版本 helper，供 finalize 与 revision 复用；既有 `audit_sha256` 名称继续兼容反馈链。
- root namespaced extension 中的 `diff_version` 保持 additive；schema `0.4` 不升级，旧报告仍可验证和 revise。

## Waves / Steps

1. 实现版本 helper、finalize 写入与结构化返回。
2. 补齐 revise 的继承、legacy 降级与所有成功返回路径。
3. 同步 Skill 与公共文档，不加入 Sopify 字段或目录约定。
4. 完成定向和全量验证，更新方案状态并在发布前停车。

## Key Decisions

- 对外只使用 `diff_version / report_version`；`artifact_fingerprint` 和反馈协议中的 `source_audit_sha256` 保持既有内部/历史语义。
- `report_version` 等于 HTML 已绑定的正式 `audit.json` 字节哈希，但不新增 HTML 字段。
- legacy schema `0.4` 报告可继续 revise，结果明确返回 `diff_version: null`，不得猜测旧 diff 身份。
- 本轮不修改 schema version；package/tag 版本使用 `0.1.0a2`。

## Constraints / Not-in-scope

- 不增加 `plan_id`、Sopify receipt、输出目录或宿主 adapter。
- 不增加 version manifest、缓存、注册表、迁移器或新 CLI 命令。
- 不重写历史报告、docs examples 或反馈字段 `source_audit_sha256`。
- 不修改原 EvidentLoop 工作区中的用户推广素材和未提交蓝图更新。

## Status / Progress

- [x] 已从远端 main `c2ea597` 建立隔离分支 `codex/feat-diff-report-version`。
- [x] 已确认当前公开版本为 package `0.1.0a1`、schema `0.4`、prompt `v0.5`。
- [x] 4 项实现与验证任务完成；370 项测试、Ruff、JavaScript 检查、构建和 release boundary 均通过。
- [x] 下一 Alpha 版本确认为 `0.1.0a2`。
- [x] 本地提交、PR 合并、tag、PyPI 和 GitHub Release 已获得用户授权。

## Next

方案实现与候选验证已完成，本方案随候选提交归档；公开发布结果由后续发布链路验证。
