---
name: literature-query
description: Literature query and cross-paper comparison skill. Main agent delegates to curate to search, synthesize, and compare insights across papers in the wiki.
---

# literature-query

## 概述

Literature query and cross-paper comparison skill. Main agent delegates to **curate** to search, synthesize, and compare insights across papers in the wiki.

**触发词**: "文献查询", "对比论文", "跨论文比较", "wiki里有没有", "查一下某篇论文", "literature query", "compare papers", "cross-paper"

## Subagent 调用链

1. **curate** — Wiki curation, quality linting, cross-paper comparison, literature queries

## 编排步骤

### Step 1: 知识检索 (main agent)

1. 使用 `wiki_get` 读取 wiki 索引，定位相关页面。
2. 提取与用户查询相关的关键事实。
3. Wiki 不足时使用 browser 补充（arXiv, Google Scholar）。

### Step 2: 派发 curate | Timeout: 600s

任务：在指定范围内执行 `query_type: "lint" | "compare" | "query"`。包含目标论文/关键词、wiki 路径、用户原始问题、已读取 wiki 页面和关键事实摘要、网络补充来源。输出要求引用 page_id 或路径、标注 evidence_level、矛盾点明确标出。

### Step 3: 质量审查

curate 产出完成后，派发 reviewer 验证（citations, evidence levels, completeness）。如果 FAIL，将修复提示发回 curate 重做。最多 2 轮修复。

### Step 4: 结果汇报

向用户呈现审查通过的结果，附 page paths 和 evidence_level 标签。

### 错误处理

- **curate 超时**: 缩小范围重试一次；fallback 到带 caveat 的直接 wiki 回答。
- **Wiki 为空**: 告知用户，建议先入库论文。
- **reviewer FAIL**: 循环回 curate（最多 2 轮）；升级给用户。

## 输入规范

| Field | Required | Description |
|-------|----------|-------------|
| query | Yes | Natural language question or comparison request |
| papers | No | Paper titles, wiki paths, or keywords to scope |
| dimensions | No | Comparison axes: methods, datasets, metrics, results |

## 输出规范

- **Query mode**: 结构化回答，带引用、证据等级、识别的缺口。
- **Compare mode**: 对齐表格，每行带 evidence_level，矛盾标记。
- **Lint mode**: Wiki 质量问题 dashboard，按类型分组，带修复建议。
