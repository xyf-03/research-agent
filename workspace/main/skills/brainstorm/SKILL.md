---
name: brainstorm
description: Research idea generation from literature. Two-stage chain: curate wiki context then ideate evidence-grounded research ideas.
---

# brainstorm

## 概述

Two-stage direct pipeline: **curate** produces quality-checked literature context, then **ideate** generates structured research idea cards. Use when the user wants research opportunities grounded in wiki evidence, not speculation.

**触发词**: "brainstorm ideas", "research ideas", "generate ideas", "research directions", "find research gaps", "科研 idea", "研究思路", "头脑风暴"

## Subagent 调用链

1. **curate** — Wiki curation, quality linting, cross-paper comparison, literature queries
2. **ideate** — Research idea generation, opportunity synthesis, deduplication, validation

## 编排步骤

### Step 0: Pre-flight

Main agent 使用 `wiki_get` 读取 wiki 索引和相关领域页面。不足时 browser 搜索 arXiv/Scholar。收集 page ID、摘要、缺口组成上下文包。

### Step 1: 派发 curate | Timeout: 900s

任务：为研究 idea 生成准备精选上下文摘要。范围包括领域/论文、关注区域。产出：跨论文比较（方法、数据集、指标、evidence_level）、lint 报告（矛盾、缺口、过时 claim）、文献摘要（局限性、未来工作信号、未验证 claim）、缺口列表（2-4 篇同类论文集群的具体痛点）。仅使用 wiki 内容，每个 claim 引用 page_id。

### Step 2: 审查 curate 产出 | Timeout: 300s

派发 reviewer 验证摘要（完整性、证据准确性、缺口具体性）。FAIL 时将修复提示发回 curate。最多 2 轮修复。

### Step 3: 派发 ideate | Timeout: 1200s

任务：从精选上下文生成研究 idea card。5-10 张 card，每张锚定到论文或 2-4 篇论文集群并命名痛点。每张 card：痛点证据、why now、提议机制、最小验证实验、预期指标、风险。去重，弱 card 标记 low-confidence。在 reply 中内联返回完整 idea card。

### Step 4: 审查 ideate 产出 | Timeout: 300s

派发 reviewer 验证 card（证据锚定、可测试实验、去重）。同样修复循环规则。

### Step 5: 呈现和回写

1. 向用户呈现摘要表和 idea card。
2. 如有 wiki 回写候选，委托 curate 更新 wiki。
3. 建议下一步（跑实验、深挖、入库更多论文）。

## 输入规范

| Field | Required | Description |
|-------|----------|-------------|
| Domain / topic | No | Scope for idea generation. Defaults to all wiki papers. |
| Paper list | No | Specific papers (titles, wiki paths, URLs). |
| Constraints | No | Methods, datasets, problems, time horizon. |

最少需要 domain/topic 或至少一个论文引用。都没有则询问用户。

## 输出规范

1. **Idea 摘要表** 供快速浏览
2. **详细 idea card** 在 reply 中内联返回，含完整证据链和验证计划
3. **Wiki 更新通知** 针对已更新页面
4. **下一步建议**
