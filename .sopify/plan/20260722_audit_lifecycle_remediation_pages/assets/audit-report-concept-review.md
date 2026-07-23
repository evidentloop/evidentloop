# Audit report 成品样例审计说明

样例文件：`audit-report-concept.html`

定位：这是 Wave 3 的可交互目标样例，不是生产 renderer 输出，也不代表真实代码审计结论。它冻结最终信息层级和交互边界，生产实现直接收敛到这套结构，不在旧模板旁增加兼容分支。

## 已冻结的最终结果

1. 页头只显示四项报告真相：审查状态、当前结论、报告级严重程度、旧问题验证结果。
2. 新链路不显示、不计算、不导出风险分；不保留旧风险/当前风险并排、变化箭头或风险等级宣传。
3. 页面标签使用“严重程度”，数据字段使用 `overall_severity`；finding 自身 severity 与人工 override 继续保留。
4. 修复链路统一命名为“修复验证 / Fix verification / `fix_verification`”。
5. 变更摘要是第一个业务区块，面向用户使用“问题”，技术身份 `finding-*` 只在核验位置出现。
6. finding 卡采用单一纵向结构：为什么是问题 → 有数据时就近显示“建议怎么改” → 只读裁定摘要 → 全宽 diff → 下方全宽操作区；不另建修复建议区块，也不展示宽泛 category 徽标。已忽略问题保留完整内容，但边线、严重度徽标和建议区使用中性配色。
7. 评论与严重度展开只向下增加高度；大于 640px 时严重度与评论左右排列，640px 及以下改为单列，不改变 diff 宽度，不使用覆盖层、悬浮栏或侧栏。
8. 代码长行不折行；只有内容实际超出时，diff 才在有最大高度的容器内上下/左右滚动；页面本身不横向溢出。
9. 375px 下 truth grid 为 2×2，裁定摘要为 2+1，finding 标题全宽，状态徽标独立，裁定与导出按钮成对并排。
10. 没有 fix verification、finding 或 feedback history 时，对应 section 连标题和空框一起省略；没有关联 fix 时，问题卡不显示“建议怎么改”。

## 数据到页面的单一链路

### audit.json · schema 0.5

- schema `0.5` 是唯一正式输入；不兼容、不转换 schema `0.4`。
- summary 保留 `review_status`、`verdict`、`overall_severity`、finding/fix counts、`basis` 和必要 notice。
- `overall_severity` 为报告级 `high / medium / low / note / null`；完整审查时由当前有效 open findings 的 severity 顺序确定，无 open finding 或审查不完整时为 `null`。
- 人工裁定 summary 保留 `model_verdict` 与 `model_overall_severity`，不保存分数或 severity delta。
- 删除 `risk_score`、`risk_delta`、`model_risk_score`、`unscored_finding_count`、`extensions.evidentloop.unscored` 以及只为是否计分存在的公开 view 字段。保留 `risk` finding category、finding severity、`pack_completeness`、downgrade provenance 与证据锚点事实；在既有 review/advisory 前置判断后，需人工分诊直接由“`downgraded_from == "bug"` 或缺少可信文件关联”判定，不保存替代字段。
- 同 diff `feedback_revision` 继续使用正式 run、events 和 human adjudication；不调用 reviewer。
- fix verification 请求必须携带 expected `source_report_version`；只接受该版本最新正式 run 中当前仍为 `open` 且 id/fingerprint 匹配的 finding。
- 跨 diff 修复验证只在 `extensions.evidentloop.fix_verification` 保存 version `1`、直接前驱身份、逐目标 finding id/fingerprint、冻结的 `source_title`、声明与 `claim_id`。
- 请求、serializer 与语义校验共用 typed 入口；extension 不重复 claim 状态、当前 verdict、当前严重程度、当前 diff identity 或绝对路径。
- 每个 claim 归属于当前 `model_review` run。reviewer 的 `Fix Verification Results` 块必须逐输入 `claim_id` 恰好一项；parser 和 completion gate 拒绝缺失、重复或未知目标。
- claim 直接保存非空 `reason`，说明为什么得到当前状态。真值表固定为：`supported`=support only、`challenged`=challenge only、`partial`=support+challenge、`unknown`=无两类 edge。schema `0.5` 的 `summary_audit.status` 支持四态和 `not_audited`：无 claim 时为 `not_audited`，全部同态时取该状态，混合时为 `partial`；页面仍按四态计数，不显示这个技术汇总。当前完整 diff 的 verdict 与 overall severity 独立计算。
- 当前 runs 只包含当前 diff 的模型审查和后续同 diff feedback revision；旧 audit 保持不可变，只作为一跳来源。

样例尾部的 `view-model-sample` 只是 renderer context 摘要，不是假装完整 `audit.json`。

### renderers/html.py

生产 context 收敛成五个只读 view：

- `report_truth`：review status、verdict、overall severity、open count、人工裁定 notice。
- `change_view`：变更标题/摘要、文件数、增删行、逐文件作用与问题入口。
- `fix_verification_view`：直接来源、冻结的 `source_title`、所选 finding、声明、逐目标 claim、证据和当前新审查结论。
- `finding_view`：model、human、current、关联 fix、feedback events、可信 hunk view；不含 `counted_in_risk`。
- `run_view`：仅当前 diff 的权威 run 顺序、问题标题和人类动作；只展示实际变化的 verdict/overall severity/open count，均未变化时显示“报告结论未变化”。删除评论与恢复模型严重度使用不同文案；没有 feedback revision 时不生成历史 section。

verdict、overall severity、claim、run 顺序和 section presence 都由 Python context 确定。模板只展示，浏览器脚本不得重新计算业务真相。

### audit.html.j2

- 用一个 truth grid 替代旧 judgment/metric 重复首屏。
- 变更摘要紧随页头；claim 保留模型原判断，关联问题全部离开 `open` 后派生显示“模型曾判断什么”和“当前裁定是什么”，并使用中性配色。文件行按当前 finding 状态显示轻量的“查看待处理/已忽略/已修复问题”入口。
- fix verification 是独立的旧问题验证区，不进入 feedback history，旧 runs 不复制到当前报告。单目标显示一个结果；多目标页头按四种 claim status 计数，正文逐目标展示，不增加第五种聚合状态。
- finding 标题与状态先说明问题；只读裁定摘要条在 diff 上方；diff 和操作区都占满内容宽度。
- 单栏 unified diff 包含文件头、增删统计、旧/新行号、红绿行和问题关键行，不引入 Diff2Html。
- `audit.json` 保留完整 hunk；超过阈值时只由 renderer 生成包含全部关键行和明确省略计数的可信节选。
- hash、schema、run id 集中到默认折叠的“报告身份与校验信息”，保留可直接选中复制的完整值。
- 原生 `<details>` / `<summary>` 负责展开状态；不建立 JavaScript 折叠状态。

### audit.js

现有反馈脚本只保留必要职责：

- identity、localStorage fallback、pending state、null 反转、JSONL、copy/download。
- 更新新 DOM 绑定、裁定摘要中的待提交变化和 aria-live 状态。
- 不排序 run，不计算 verdict/overall severity，不判断 claim，不根据 finding 消失宣布修复。
- 不决定 section 是否存在、页头颜色、diff 配对或 details 展开状态。
- fix verification 是 renderer 输出的只读结果，不建立第二份浏览器状态。

## 移动端收口

- 不为移动端复制组件或模板；只用同一 DOM 和响应式 CSS。
- 保持 16px 正文和操作文字、44×44 最小触控区、可见焦点、skip link、live region 与 reduced motion。
- 减少嵌套内边距，但不压缩证据内容；truth grid 2×2，裁定摘要 2+1。
- finding 标题与路径占满一行宽度，问题严重度与待处理状态放入紧凑徽标组。
- 裁定按钮、导出按钮各自两列；评论表单单列向下展开。
- diff 文件头与节选说明保持在滚动区外；局部双向滚动，滚动到边界后继续浏览整页。

## 整体删除边界

实现时必须作为同一个 schema/summary/renderer 改动删除：

- schema 中的 `risk_score`、`risk_delta`、`model_risk_score`、`unscored_finding_count`、`extensions.evidentloop.unscored` 及其 required/validation 规则。
- `audit/summary.py` 的 `SEVERITY_WEIGHTS` 和风险分计算。
- feedback revision 与 semantic validation 中的风险快照、delta、模型风险字段和比较。
- renderer context、模板、CSS、fixture、测试、README/Pages 中的风险分 label、metric 与旧/当前风险对照。
- `html.py` 中无模板消费者的 `revision`、`human_findings`、`next_section_number`，以及只服务旧 judgment grid 的计数字段。
- 旧 judgment grid/card CSS、动态章节编号、body `overflow-x: hidden` 掩盖方案。

删除必须端到端同时完成，不能先隐藏 UI、保留旧计算，也不能给新字段套旧风险算法的别名。

## 明确保留与非目标

- 保留 `risk` finding category、finding severity、model judgment、human adjudication、feedback JSONL、report/diff version、`pack_completeness`、downgrade/锚点事实、完整 hunk、renderer 单一可信节选和 localStorage 失败回退。
- 保留 Jinja autoescape、StrictUndefined、自包含 CSS/JS 与 HTML trace validator。
- 不做浏览器旧报告选择、自动 finding 匹配、audit series、中央 registry、backlog 或工单系统。
- 不引入前端框架、设计系统、图表、暗色主题、双栏 diff、搜索/复杂筛选、常驻侧边栏、语法高亮依赖、同步滚动、全屏模式或复杂动画。

## 样例验收

- 桌面无需阅读 hash 即可区分 review status、当前 verdict、严重程度和旧问题验证结果。
- 页头和 view model 都没有风险分；`schema_version` 为 `0.5`，summary 示例使用 `overall_severity`。
- view model 的来源 target 含冻结的 `source_title`；独立 HTML 不回读旧 audit 也能展示旧问题与用户声明。
- expected/actual source version 与当前 open 资格在任何输出副作用前验证；claim 结果缺失、重复、未知或 edge/status 不一致时报告不得标记 complete。
- 变更摘要能直达问题证据，用户界面不出现裸露的英文 `finding`。
- 裁定摘要、全宽 diff、全宽操作区顺序稳定；展开表单只向下增长。
- 长行和多行节选只在 hunk 内滚动；文件头、节选计数和操作区始终独立可见。
- 375px 下无页面整体横向滚动，truth grid、裁定摘要、标题/徽标和按钮保持冻结结构。
- 键盘可到达 skip link、diff 滚动区、details、裁定、select、textarea、复制和下载。
- 清空评论生成 `comment: null`；恢复模型严重度生成 `severity: null`。
- 状态不只依赖颜色；复制失败明确说明数据未丢失并提供下载路径。
