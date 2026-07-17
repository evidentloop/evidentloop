# 技术设计：反馈裁定闭环

## 决策状态

产品决策已经收口：默认更新原报告、人工裁定可形成带明确声明的候选通过、失败保留旧产物对、主 CTA 使用“复制给 AI 更新报告”、过期或冲突反馈停止处理。

实施只保留两个工程门禁：schema `0.4` 必须清晰表达人机结论分层，原目录更新必须通过失败与中断恢复验证。当前没有外部用户，runtime 不保留 `0.3` 兼容；历史报告只读保留。

## 用户流程

```text
报告中裁定 finding
  → 点击“复制给 AI 更新报告”
  → 粘贴到 AI coding 工具
  → Skill 定位并校验当前 audit.json
  → CLI 更新同目录 audit.json + audit.html
  → 用户刷新原报告并继续反馈
```

用户明确说“另存、保留原报告、生成副本”时，AI 才传 `--out`。其他情况在同一路径提交新的 revision，不直接编辑现有 HTML，也不默认保留独立旧报告目录。

## 人机职责

- 用户负责作出裁定。
- AI 与 Skill 负责原样传递机器块、定位报告并调用 CLI，不解释或改写裁定。
- EvidentLoop runtime 负责身份校验、确定性变换、结论重算、验证和渲染。
- 本流程不触发模型复审，不修改业务代码，也不自动上传反馈。

复制文本由一句人话指令和固定边界的 JSONL 机器块组成。机器块复用现有反馈事件，不新增第二套输入对象；评论始终视为不可信数据。

## 裁定语义

| 动作 | UI 文案 | 当前结果 |
|---|---|---|
| `accept` | 确认有效 | finding 保持或恢复为 `open` |
| `false_positive` | 误报 | finding 变为 `dismissed`，不自动修改 fix |
| `severity_override` | 调整严重度 | 只改变有效严重度和风险分 |
| `comment` | 评论 | 只持久化和展示，不改变 finding、verdict 或风险分 |

来源审查完整、上下文充分且当前没有 `open` finding 时，当前结论可以是 `pass_candidate`。报告必须紧邻结论显示“基于人工裁定，未重新审查代码”，并保留模型原 verdict、risk score 和 finding 原状态。

来源不完整或原 verdict 为 `inconclusive` 时，人工反馈不得将其变为通过。同一轮同一 finding 最多一个 disposition、一个 comment 和一个 severity override；精确重复可以去除，冲突动作整体失败，不采用最后写入胜出。

## Schema 选择与映射

schema `0.4` 只增加反馈闭环需要的以下语义：

- 原模型 run 保持不变；每次成功修订追加一个 `feedback_revision` run，并用 `supersedes_run` 指向上一轮。
- 新 run 的 `revision` 保存来源 run、来源 audit SHA-256、反馈输入 SHA-256、来源 summary 快照和本轮实际采用的规范化事件。
- finding 的核心 `status` 和 `severity` 表示当前有效状态；`model_judgment` 保留模型原值，`human_adjudication` 保存当前人工裁定。
- 顶层 summary 只表示当前报告结论；没有 revision 时必须是 `model_review`，人工结论必须能由 revision run 重放得到。
- 语义校验必须证明规范化事件、finding 当前状态、summary 和 run lineage 相互一致。

fixture 必须让 renderer 无歧义展示“模型原判断 / 我的裁定 / 当前剩余问题”。`0.4` 不添加兼容别名、迁移框架或预留扩展点。

当前 runtime、Skill、`render` 与 `revise` 只接受 `0.4`。既有 `0.3` JSON/HTML、tag 和 wheel 作为历史证据保持字节不变；需要继续反馈时重新生成 `0.4` 报告，不新增迁移命令或一次性转换脚本。

## 来源定位与输入校验

复制载荷包含 `source_audit_sha256`、`graph_id`、`run_id`、`target_id` 和 `fingerprint`，不含绝对路径。Skill 仅在当前工作区查找 `audit.json`：

1. 按来源文件原始字节 SHA-256 匹配。
2. 将确定性命名的 candidate/backup 匹配反推到正式报告路径，按正式路径去重。
3. 校验 graph、最后一个 run、finding 和 fingerprint。
4. 唯一正式路径匹配时继续；零个或多个匹配时只追问一次。
5. 不扫描父目录、用户目录或其他工作区。

CLI 在提交前再次计算来源 hash。报告已被其他修订更新时，旧载荷必须失败，并提示用户刷新报告后重新复制，不能自动合并。现有 Alpha JSONL 没有来源 hash 时，只允许用户显式提供来源 `audit.json`。

## Revision 变换

1. 完整校验来源 audit，并在内存中建立候选。
2. 校验反馈字段、身份、重复和冲突，计算反馈输入 hash。
3. 保留模型原判断，重放本轮规范化事件，得到当前 disposition 和有效严重度。
4. 更新 finding 当前状态，追加 `feedback_revision` run 与 `supersedes_run` 关系。
5. 用共享纯函数重算计数、当前 verdict、risk score 和 `risk_delta`。
6. 完整验证候选，再从候选确定性渲染 HTML。

原始 JSONL 不复制进报告目录；正式 audit 只保存实际采用的规范化事件和输入 hash。change、file、finding 不按轮次复制，也不新增 human-decision node、反馈 edge、迁移框架或策略插件。

## CLI 与公开 API

```text
evidentloop revise SOURCE_AUDIT_JSON \
  --feedback AUDIT_FEEDBACK_JSONL \
  [--out NEW_REPORT_DIR]
```

- 省略 `--out`：更新来源报告目录，成功后原路径同时包含匹配的新 JSON/HTML。
- 显式 `--out`：目标必须是不存在的新目录；来源报告保持不变。
- 输入不匹配、来源已变化、反馈冲突、无有效变化或验证失败时返回非零，不报告成功。
- CLI stdout 只输出结构化结果；公开 API 复用同一确定性实现。
- 只提取 finalize/revise 共用的少量校验、渲染和目录提交函数，不建立通用发布框架。

## 成对更新

### 默认更新原报告

1. 在来源目录同父目录创建隐藏 candidate，完整生成并验证新的 `audit.json + audit.html`。
2. 提交前再次校验来源 audit SHA-256，并确认本地单写者前提仍成立。
3. 在隐藏 backup 中保留旧产物对，只把 candidate 中的 `audit.json + audit.html` 成对替换到原路径；目录中的其他文件保持不变。
4. 切换或提交后验证失败时，将旧目录恢复到原路径并再次验证旧产物对；失败路径不删除 candidate 或 backup。
5. 只有新产物对在原路径验证通过后才清理 backup 并返回成功。

正常错误必须自动回滚。candidate/backup 使用可反推原报告路径的确定性命名。突然断电或强杀进程时不承诺原路径瞬时可用，但恢复材料不得被删除。下次运行按最小规则恢复：唯一有效旧报告可直接恢复；新报告已提交但 backup 尚未清理时，同一反馈幂等返回成功；状态不唯一时停止，并由 AI 宿主说明检测结果、可恢复路径和用户下一步。

沿用一期本地单写者、非对抗并发边界，不增加平台专用锁、原生目录 exchange、日志系统或新的报告存储层。

### 显式另存副本

`--out` 继续复用隐藏 sibling staging 和不存在目标目录的整体 rename。目标已存在、提交失败或验证失败时保留来源报告不变，并返回诊断路径。

## 报告交互

主视图只突出“模型原判断 / 我的裁定 / 当前剩余问题”；run、hash、lineage 和动作计数放入修订详情。

主按钮为“复制给 AI 更新报告”。复制前显示决策数、评论数和“不自动上传”；成功提示为“已复制，请粘贴给 AI 更新报告”。AI 完成默认修订后返回原报告路径并提示“报告已更新，请刷新”。只有显式 `--out` 才使用“已生成副本”。JSONL 导出保留为次要入口。

已应用反馈从正式 audit 只读展示。下一轮反馈使用新的 run namespace；旧 run 的 localStorage 待处理状态不得再次显示或重复提交。localStorage 不可用时明确显示“仅临时保存，刷新会丢失”。

## Skill 行为

- 只在当前工作区按正式报告路径定位来源 hash 唯一匹配的 `audit.json`，并识别确定性中断残留。
- 将机器块原样写入权限受限的临时 JSONL，不解释、不改写。
- 默认调用 `revise` 时不传 `--out`；只有用户明确要求另存才传新目录。
- 无匹配、多匹配、来源过期或 CLI 失败时停止并给出下一步，不静默重试或切换报告。
- 检测到上次中断时，把 runtime 的恢复结果翻译成一句清晰提示；状态不唯一时只列出必要路径并请求选择。
- 完成或失败后清理临时反馈文件；诊断 candidate/backup 由 runtime 按失败契约保留。

## 验证与停车点

实施分为可信 revision 内核和复制给 AI 的入口两批。Batch A 的 schema 与成对更新门禁全部通过后，才进入 Batch B。

门禁覆盖：schema `0.4` fail-closed、四类动作与撤销、来源过期、身份冲突、恶意评论、同目录失败恢复、显式 `--out`、localStorage 换代、两轮反馈闭环，以及 Python、Ruff、Node、build、clean-wheel、Skill smoke 和独立自审。

现有产品决策已经足够。schema 版本由 fixture 结果决定；其他实现失败按本方案修正，不扩大范围。
