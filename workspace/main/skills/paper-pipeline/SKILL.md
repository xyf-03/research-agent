---
name: paper-pipeline
description: End-to-end deep paper analysis and validation. Orchestrates 6 subagents in a strict linear chain from ingestion to quality audit.
---

# paper-pipeline

## 概述

End-to-end deep paper analysis and validation. Orchestrates 6 subagents in a strict linear chain from ingestion to quality audit.

**触发词**: "完整分析", "full pipeline", "deep review", "S1-S6", "全流程分析", "paper pipeline", "端到端审稿"

## Subagent 调用链

| # | Agent | Stage | Role |
|---|-------|-------|------|
| 1 | **ingest** | S1 | Paper PDF ingestion, structured wiki page creation |
| 2 | **extract** | S2 | Deep experiment extraction from paper text |
| 3 | **critic** | S3 | Reviewer-perspective problem and claim analysis |
| 4 | **design** | S4 | Validation experiment design for identified problems |
| 5 | **spec** | S5 | Implementation spec and claude-code task prompt generation |
| 6 | **audit** | S6 | Cross-stage quality auditing and consistency check |

## 编排步骤

### Pre-pipeline

使用 `wiki_search` 检查论文条目是否已存在。如有则记录 page ID 给下游；否则 S1 ingest 会创建。

### 各阶段概要

**S1 — ingest** | Timeout: 900s
- 任务：将论文入库。按 Capture→Extract→Create Paper Page→Update Index 流程执行。
- 产出：Wiki page path, raw source path, evidence_level
- 门禁：Wiki page >= 100 lines, 至少一个数值结果

**S2 — extract** | Timeout: 1800s
- 任务：对论文执行实验深度提取。使用 paper-experiment-deep-extractor skill。在 reply 中返回完整 12 节实验提取文档（## 0–## 11）。
- 输入：S1 的 wiki 路径，PDF 作为 fallback
- 门禁：Reply 包含全部 12 节

**S3 — critic** | Timeout: 1200s
- 任务：对论文执行审稿式问题分析。S2 实验提取文档嵌入 task 中传递。
- 输入：Wiki 路径，S2 实验文档
- 门禁：>= 1 个有证据可追溯性的具体问题

**S4 — design** | Timeout: 1200s
- 任务：执行验证实验设计。S3 问题分析文档嵌入 task 中传递。返回完整 10 节验证实验设计文档（## 0–## 9）。
- 输入：Wiki 路径，S3 问题文档
- 门禁：Reply 包含全部 10 节；每个实验映射到 S3 问题并有预期结果

**S5 — spec** | Timeout: 600s
- 任务：生成 claude-code 任务提示词。S3+S4 产出嵌入 task 中传递。
- 输入：S3 + S4 产出，可选代码仓库
- 门禁：文件级别具体，无未填充的占位符

**S6 — audit** | Timeout: 600s
- 任务：执行流水线质量审计。S2-S5 完整产出嵌入 task 中传递。
- 输入：全部 S2-S5 产出
- 门禁：覆盖全部 6 个审计维度；blocking issues 可操作

### 错误处理

- **阶段失败**: 记录失败，告知用户阶段 + 错误详情。提供重试或 checkpoint 恢复。
- **Checkpoint 恢复**: 记录已完成阶段及其完整产出内容。从请求的阶段继续时，验证所有前置阶段内容可用。
- **质量门失败**: 将上一产出 + 修复指令重新发给同一 agent。每阶段最多重试一次。

## 输入规范

| Field | Required | Description |
|-------|----------|-------------|
| Paper title | Yes | Full paper title |
| PDF path or URL | Yes | Absolute path or accessible URL |
| Code repo | No | Local path or remote URL |
| User notes | No | Focus areas, constraints, questions |
| Start stage | No | Default S1; set to "S3" etc. for checkpoint resume |

## 输出规范

| Stage | Agent | Content |
|-------|-------|---------|
| S1 | ingest | Wiki page path, evidence_level |
| S2 | extract | Structured experiment extraction (12-section Markdown) |
| S3 | critic | Prioritized problem and claim analysis (8-section Markdown) |
| S4 | design | Validation experiment designs (10-section Markdown) |
| S5 | spec | Ready-to-use claude-code task prompt (Markdown) |
| S6 | audit | Cross-stage quality audit report (Markdown) |

用户收到：top 3 问题，优先验证实验，审计结论，下一步建议。
