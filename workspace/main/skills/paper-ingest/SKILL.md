---
name: paper-ingest
description: Two-stage pipeline to ingest a paper into the research wiki and verify quality. Ingest creates the wiki page, curate lints for consistency.
---

# paper-ingest

## 概述

Two-stage pipeline to ingest a paper into the research wiki and verify quality: ingest creates the wiki page, curate lints for consistency.

**触发词**: "入库", "ingest paper", "add to wiki", "文献笔记", "整理这篇论文"

## Subagent 调用链

1. **ingest** — PDF ingestion, text extraction, structured wiki page creation
2. **curate** — Quality linting, metadata verification, cross-page consistency check

## 编排步骤

### Pre-check (main agent)

1. 使用 `wiki_search` 检查已有条目。如已存在且用户未要求重新入库则跳过。
2. 验证用户提供了 PDF 路径或 URL。如都没有则询问。
3. 记录论文元数据供下游使用。

### Step 1: 派发 ingest | Timeout: 1800s

任务：将论文入库。按 Capture → Extract → Create Paper Page → Update Index 流程处理。完成后汇报入库位置和 evidence_level。

### Step 2: 派发 curate | Timeout: 600s

ingest 完成后，派发 curate 对新入库页面执行质量检查：frontmatter 完整性、evidence_level 一致性、Results 具体数字、孤立链接、矛盾 claim、index 条目正确性。输出 lint report。

### Step 3: 向用户汇报

- **Curate 通过**: 汇报 wiki 路径、evidence_level、关键元数据。建议下一步（paper-review, idea-generate, cross-paper compare）。
- **Curate 发现阻塞问题**: 向用户汇报问题，不自动重新派发 ingest。

### 错误处理

| Stage | Failure | Action |
|-------|---------|--------|
| ingest | PDF 不可读 | 询问用户替代来源 |
| ingest | 提取不充分 | 建议手动 abstract 录入 |
| curate | 阻塞 lint 问题 | 汇报用户，等待指示 |

## 输入规范

| Field | Required | Description |
|-------|----------|-------------|
| PDF path or URL | Yes | Absolute path or accessible URL |
| Title | Recommended | Extracted from PDF if omitted |
| User notes | Optional | Focus areas or special instructions |
