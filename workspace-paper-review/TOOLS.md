# TOOLS.md - 本地说明

这个工作区主要依赖 skill 工作流，本身没有额外的设备或账号约定。

## 约定

- 输出优先使用 Markdown，方便直接落到 Obsidian 或仓库里。
- 生成 Codex 提示词时，要强调“基于现有代码改动”，不要写成泛泛的论文说明。
- 可复用的流程经验放进 `MEMORY.md`。

## 工作区内技能

- `paper-experiment-deep-extractor`（S2）
- `paper-review-style-problem-analyzer`（S3）
- `paper-validation-experiment-designer`（S4）
- `claude-code-validation-task-prompt-generator`（S5）
- `paper-pipeline-quality-auditor`（S6）

> Wiki 整理（`paper-wiki-entry-organizer`）由 `autoresearch` 子 agent 负责，不属于本 agent 的技能范围。

## Wiki 工具（memory-wiki，isolated 模式）

本 agent 不直接维护 wiki（那是 autoresearch 的活儿），但 5 个 pipeline 阶段经常需要查既有 wiki 条目。优先用 memory-wiki 工具，**只读不写**：

- `wiki_status` — 确认 vault 在线且 isolated 模式下可读。
- `wiki_search` — 搜既有论文条目 / 相关 claim / 已记录的实验设计；用 mode flag 区分 person、question、source、raw claim。
- `wiki_get` — 按 id/path 拉单页详情，feed 给后续 review / validation 设计。
- `wiki_lint` — 引用 wiki 内容前如果担心 provenance，跑一次确认没有 contradiction 或 open question 影响结论。

如果发现 wiki 缺条目或需要更新，**不要自己用 `wiki_apply`**，把缺口写回 main agent，由 main 委派 autoresearch 处理。

Dashboard（`reports/open-questions.md`、`reports/contradictions.md` 等）用 `wiki_get` 读。
