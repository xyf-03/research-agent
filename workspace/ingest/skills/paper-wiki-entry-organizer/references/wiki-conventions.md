# Wiki 管理规范

Wiki 的命名、索引、日志、链接和维护规则。

## 命名规范

- 文件名使用小写 kebab-case
- Wiki 页面使用稳定、描述性的 slug
- Domain 文件夹使用小写 kebab-case
- Raw 文本源命名为 `YYYY-MM-DD-short-title.ext`
- Raw PDF 使用发表日期或 arXiv 日期：`YYYY-MM-DD-short-title.pdf`
- 论文页 slug 通常匹配论文标题（不含日期前缀）
- 方法、数据集、任务、指标、概念、实体和主题页不包含日期（除非页面本身是时间绑定的）
- 分析和比较页可在与特定问题或快照绑定时包含日期

## Index 规则

wiki index 页面是内容导向的目录，人类和 agent 都应可读。

- 按领域优先组织，再按页面类型
- 对研究领域，展示 papers、methods、datasets、tasks、metrics、concepts、topics、comparisons、analyses
- 条目简短可扫描，每条有简要描述
- 有用时包含 evidence level 或 source count
- 同一节内优先字母排序（除非时效性更重要）
- 包含开放阅读队列或高价值开放问题
- 每次添加或实质性更改持久页面时更新 index

推荐条目格式：

> - 页面标题（相对路径）：一句话摘要。Evidence: full-paper。Updated: YYYY-MM-DD。Sources: N。

## Log 规则

wiki log 页面是按时间排列的追加式记录。

- 每条以 `## [YYYY-MM-DD] action | title` 开头
- 动作类型：setup / ingest / query / analysis / compare / lint / schema / organize
- 记录变更文件、关键发现和未解决问题
- 条目简洁但信息充分

推荐条目格式：

> ## [YYYY-MM-DD] ingest | Paper Title
> - Raw source: 相对路径
> - Updated: 变更的页面路径列表
> - Evidence level: full-paper
> - Key takeaways: 一两条值得记住的要点
> - Open loops: 未解决问题或 none

Log 是追加式的，不要重写历史条目（除非用户要求）。

## 链接规则

- 使用相对 markdown 链接，不使用绝对本地文件路径
- 每个新页面至少从一个现有页面和 wiki index 页面链接
- 当论文为已有的方法、数据集、任务、指标、概念、主题或比较页面提供信息时，更新该页面
- 从可复用研究对象页面链接回支撑它们的论文页面
- 当页面引用多个相关页面时，添加 Connections 章节
- 如果一个页面变得核心，确保多个其他页面链接到它

## 页面创建启发式

在以下至少一个条件成立时创建新的持久页面：

- 该论文、方法、数据集、任务、指标、概念或实体是用户研究的核心
- 该条目出现在多个来源中
- 该页面可能被再次访问
- 内容会使多用途页面膨胀
- 用户明确希望追踪该主题
- 一个比较页面能防止重复的临时推理

不要为每个偶然提及创建页面。

## 维护启发式

- 优先原地编辑而非创建重复页面
- 当两个页面明显代表同一事物时合并
- 页面被取代时标记 superseded 并指向新的规范页面
- 页面重要但连接薄弱时，从相关页面或 index 添加入站链接
- 页面过期时，在下一个相关的 ingest 或 query 时刷新
- 页面放错位置时，优先在 domains 子树内用 wiki 工具移动而非复制
- 迁移期间保留旧的 sources/ 链接，直到对应的 papers/ 页面存在且入站链接已更新

## 矛盾与不确定性

- 不因新论文不同意就擦除旧 claim
- 用新 claim 更新相关页面并注明冲突
- 优先使用 Tensions、Disagreements、Caveats 或 Open Questions 章节而非隐藏歧义
- 信心低时直接说明
- 评估设置不同时，先描述不匹配再比较结果
- 基于 abstract-only 或 skimmed 证据的 claim 标注该限制

## 注意事项

- Ingest agent 不调用 `sessions_spawn`，所有任务在自身 session 内完成
- 产出通过 `wiki_apply` 写入 wiki vault，不写入文件系统
- 一论文一处理，不批量
