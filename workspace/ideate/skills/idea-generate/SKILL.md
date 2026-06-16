---
name: idea-generate
description: 从论文、wiki、实验结果和用户约束中生成有证据支撑、可比较、可验证的研究 idea card。
---

# Idea Generate

## Overview

Generate candidate research ideas from evidence. Intake wiki pages, paper-review outputs, experiment logs, failed attempts, repository context, and user preferences. Summarize the research landscape, propose improvement ideas, filter and rank them, and return the most recommended ideas inline in the reply text.

不产生无约束的头脑风暴。产生有论文证据支撑、可并排比较、可进入人工审查或下游评估的 idea。每个 idea 必须针对来自具体论文/wiki 页面或 2–4 篇同类论文集群的一个具体痛点；没有命名痛点的宽泛方向不是有效的 idea card。

## Required Inputs

生成 idea 前，构建 Idea Generation Brief（参考 `references/brief-template.md`）：

- `research_topic`（必需，可从论文标题或用户上下文推断）
- `target_task`、`current_baseline`、`available_data`、`available_code`
- `available_compute`、`preferred_metrics`、`hard_constraints`
- `known_failures`、`desired_risk_level`

缺失字段保守推断并标注为假设。仅当没有研究主题、没有证据材料或硬约束无法解决时才追问。

## Core Workflow

1. 将请求标准化为 Idea Generation Brief
2. 从用户提供的材料、wiki 页面、实验结果、失败尝试、代码约束构建上下文摘要
3. 定位论文文件夹（默认 `<workspace>/paper`），提取论文文本和局限性/未来工作信号
4. 写 `paper-analysis.md`（逐论文摘要、跨论文发现、局限性/缺口、可迁移洞察）
5. 写 `draft-ideas.json`（5–10 张候选 Idea Card）
6. 去重，保留每个集群中最强的变体
7. 用 `references/idea-card-template.md` 验证每张 card
8. 轻度评分：证据强度、可测试性、可行性、新颖性、预期影响
9. 输出推荐 Idea Card
10. 在 reply 中内联返回完整 recommended-ideas.md 内容
11. 收到用户反馈后，返回修订后的输出

使用 `references/generation-strategies.md` 中的策略生成 idea：gap-driven, contradiction-driven, transfer-driven, failure-driven, ablation-driven, metric-driven, constraint-driven。

## Hard Rules

1. 每个 idea 以证据为基础
2. 每个 idea 锚定到一篇具体论文/wiki 页面或 2–4 篇同类论文集群；显式命名来源
3. `target_problem` 必须是具体痛点，不是宽泛研究领域或方法族标签
4. 每个 idea 包含最小验证实验
5. 每个 idea 命名至少一个预期变化的指标
6. 每个 idea 标识一个风险或失败模式
7. 弱支撑 idea 标记为 `low-confidence`
8. 优先 5–10 个高信号 idea，而非冗长嘈杂列表
9. 不声称论文说了什么除非出现在来源中
10. 准备 idea 供人工审查或下游评估；不在 skill 内宣布最终赢家

## Output Structure

最终 reply 中内联返回完整 recommended-ideas.md 内容（详见 `references/output-spec.md`，paper demo 场景见 `references/paper-demo-output-spec.md`），附简短摘要：
1. 处理论文数
2. 推荐 idea 数
3. Wiki writeback candidates（当 idea 锚定到 wiki 论文时）

每张 Idea Card 遵循 `references/idea-card-template.md`：

```text
idea_id:
title:
one_sentence_hypothesis:
anchor_sources:
target_problem:
mechanism:
paper_insight_or_limitation:
evidence_chain:
minimum_experiment:
expected_metric_change:
implementation_scope:
risks:
confidence:
recommendation_reason:
wiki_writeback:
```
