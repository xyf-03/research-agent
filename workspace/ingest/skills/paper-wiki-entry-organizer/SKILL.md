---
name: paper-wiki-entry-organizer
description: Paper PDF ingestion workflow for the Ingest agent. Convert a PDF into a structured wiki paper page following the 11-section template with full evidence traceability.
---

# Paper Wiki Entry Organizer

## Purpose

将研究论文 PDF 摄入并创建结构化 wiki 论文页面。Ingest agent 的核心能力：论文 PDF 摄入 → wiki 页面创建。

## When To Use

- 新论文 PDF 需要加入 wiki
- 用户请求"入库这篇论文"或"加入 wiki"
- raw/inbox/ 中有待处理的论文

不要用于：
- 文献查询（由 curate agent 处理）
- 跨论文比较（由 curate agent 处理）
- Wiki 质量审计（由 curate agent 处理）

## 输入

- `pdf_path`: 源 PDF 路径（raw/inbox/ 或 raw/sources/）
- `target_domain`: 论文所属领域子树
- `evidence_level`: 基于 PDF 访问程度（默认：全文提取成功则为 full-paper）

## Final Reply / 调用者交付

最终 reply 必须直接返回调用者要求的完整内容本体；文件、wiki 写入、日志或路径不能替代 reply。不要只回复“已完成”“已写入”“见路径”“NO_REPLY”。如果本 skill 生成 Markdown 文档、idea cards、报告、评分或任务提示词，必须在 reply 中内联输出完整正文。

## 输出

- raw/sources/ 下的规范命名 PDF 和提取全文
- 通过 `wiki_apply` 创建结构化论文页面（slug 在目标领域下）
- 通过 `wiki_apply` 更新 wiki 索引和日志

论文页面必须包含：
- 全部 frontmatter 字段
- 论文专属 frontmatter（paper.title, paper.authors, paper.year, paper.venue, paper.arxiv, paper.doi, paper.code, classification.*, evidence_level）
- 全部 11 节（Citation, One-Sentence Contribution, Problem Setting, Method, Experiments, Results, Limitations, Reusable Claims, Connections, Open Questions, Provenance）

## Ingestion 流程（Execute-Verify-Report）

### Step 1: Capture
捕获 raw source，规范命名移入 raw/sources/。验证文件存在、可读、非空。失败重试一次。

### Step 2: Extract
提取全文到 raw/sources/。验证文本长度足够、包含论文结构。失败尝试替代方法一次。

### Step 3: Create Paper Page
使用 `wiki_apply` 按 11 节模板（见 `references/page-templates.md`）创建论文页面。填写全部 frontmatter 字段，设置 evidence_level。验证页面 >=100 行、有 evidence_level、Results 有具体数字。失败补充缺失部分，最多一次重试。

### Step 4: Update Index
使用 `wiki_apply` 更新 wiki 索引和日志。验证索引链接正确、日志为追加式。

## 最低可接受产出

- 一个 raw source 已捕获
- 一份全文已提取
- 一个论文页面已通过 wiki 工具创建（>=100 行，有 evidence_level，Results 有具体数字）
- Wiki 索引和日志已更新

## 质量规则

遵循 `references/wiki-conventions.md` 中的命名、索引、日志和链接规范。此外：

- 不编造 claim——每条 claim 追溯到论文页章节
- Experiments 必须包含数据集大小、baseline 名称、训练超参
- Results 必须为每个 main claim 包含具体数字
- 页面用中文；保留原始论文标题、作者、DOI、arXiv、代码链接的原文
- 缺失信息标注"原文未报告"
- 更新已有页面优先于创建重复页面
