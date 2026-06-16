---
name: benchmark
description: Benchmark execution and evaluation skill. Orchestrates QA benchmarks, collects candidate answers, and routes them through the judge subagent for quality-gated scoring.
---

# benchmark

## 概述

Benchmark execution and evaluation skill. Orchestrates the main agent through running QA benchmarks, collecting candidate answers, and routing them through the judge subagent for quality-gated scoring.

**触发词**: "run benchmark", "run eval", "跑 benchmark", "评估", "benchmark 评测", "QA 测评"

## Subagent 调用链

1. **judge** — Independent quality gate. Produces PASS/FAIL/NEEDS_HUMAN_REVIEW verdicts, numeric scores (0-1), and actionable fix prompts. Evaluates against gold_answer, must_contain, rubric, and pass_threshold.

## 编排步骤

### Step 1: 加载 benchmark 规格

- 读取 `benchmarks/<name>/qa.jsonl` 加载 QA 条目
- 每条包含：`question`, `gold_answer` (可选), `must_contain` (可选), `rubric` (可选), `pass_threshold` (可选)

### Step 2: 执行 QA

- 对每条 QA，通过正常任务路由处理问题
- Main agent 可按需委托子 agent
- 收集候选答案（最终 reply 文本）

### Step 3: 派发 judge 评分 | Timeout: 300s

任务：根据 gold_answer、must_contain、rubric、pass_threshold 评估候选答案。输出 VERDICT、SCORE (0.00-1.00) 和 rationale。FAIL 时提供 Fix prompt。

### Step 4: 处理 judge 结论

- **PASS**: 记录分数，计入 pass_rate
- **FAIL**: 可选发回重试（每 QA 最多 1 次），重试后重新评分
- **NEEDS_HUMAN_REVIEW**: 标记待人工关注

### Step 5: 汇总和报告

- 计算 `pass_rate` = 通过数 / 总数
- 计算 `avg_score` = 所有分数的均值
- 输出 `bench-report.json` 含 `pass_rate` 和 `avg_score`
- 向用户呈现含逐条分解的摘要

### 错误处理

- Judge spawn 失败: 记录错误，标记 NEEDS_HUMAN_REVIEW，score 0，继续剩余条目
- 超时: 标记超时，score 0，继续
- 无效 QA schema: 跳过条目，记录警告，不中止全部运行

## 输入规范

**命名 benchmark 运行:**
- Benchmark 名称（必须匹配 `benchmarks/` 下的目录）
- 可选：指定 QA 索引（默认全部）

**Ad-hoc 评估:**
- 问题文本
- 候选答案
- 评估标准：gold_answer, must_contain, rubric, pass_threshold（任意组合）

## 输出规范

**bench-report.json:**
```json
{
  "benchmark": "{name}",
  "pass_rate": 0.00,
  "avg_score": 0.00,
  "items": [
    {
      "index": 0,
      "verdict": "PASS|FAIL|NEEDS_HUMAN_REVIEW",
      "score": 0.00,
      "summary": "..."
    }
  ]
}
```
