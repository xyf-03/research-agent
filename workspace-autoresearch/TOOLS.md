# TOOLS.md - Local Notes

## 论文处理

- PDF 全文提取优先用本地 PDF 解析，摘要获取可用 arXiv API
- 论文元数据：CrossRef / Semantic Scholar API 补充 DOI、引用信息
- 代码仓库：GitHub 链接记录在 paper frontmatter 的 `code` 字段

## 工作空间

- `raw/` — 不可变原始文件，规范命名 `YYYY-MM-DD-short-title.ext`
- `wiki/` — 维护层，中文呈现，按 domain 分层
- `wiki/index.md` — 第一检索入口，每次 durable page 变更后更新
- `wiki/log.md` — 追加式时间线，每次操作后记录

## 为什么分开

Skills 定义工具怎么用，这个文件记录本 agent 特有的配置和路径。分开意味着更新 skills 不会丢失本地笔记。

## Wiki 工具（memory-wiki，isolated 模式）

Wiki 是本 agent 的主战场。优先用 memory-wiki 工具操作，**不要**直接读写 `~/.openclaw/wiki/main/` 文件树。

- `wiki_status` — 查 vault 模式 / 健康度 / Obsidian CLI 状态；每次会话首次写 wiki 之前先跑一次。
- `wiki_search` — 搜 wiki 页面；通过 mode flag 切换 person lookup / question routing / source evidence / 原始 claim 钻取。
- `wiki_get` — 按 id 或 path 读单页；找不到时会回落到 shared memory corpus。
- `wiki_apply` — 做有限范围的 synthesis 或 metadata 修改，比手写页面更稳。
- `wiki_lint` — 跑 provenance gap / contradiction / open question 结构检查；每次大批量改 wiki 后必跑。

Dashboard 自动写到 `~/.openclaw/wiki/main/reports/`（`open-questions.md`、`contradictions.md`、`stale-pages.md`、`claim-health.md` 等）。要查 wiki 健康度时用 `wiki_get` 读这些 dashboard，不要扫文件。
