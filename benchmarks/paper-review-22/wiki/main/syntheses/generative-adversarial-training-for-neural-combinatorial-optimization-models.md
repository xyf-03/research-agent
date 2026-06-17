---
pageType: synthesis
id: synthesis.generative-adversarial-training-for-neural-combinatorial-optimization-models
title: generative-adversarial-training-for-neural-combinatorial-optimization-models
sourceIds:
  - raw/sources/2021-10-generative-adversarial-training-for-neural-combinatorial-optimization-models.pdf
status: active
updatedAt: 2026-06-17T03:09:43.928Z
---

# generative-adversarial-training-for-neural-combinatorial-optimization-models

## Notes
<!-- openclaw:human:start -->
<!-- openclaw:human:end -->

## Summary
<!-- openclaw:wiki:generated:start -->
---
type: paper
domain: machine-learning
status: active
created: 2026-06-17
updated: 2026-06-17
tags:
  - combinatorial-optimization
  - adversarial-training
  - reinforcement-learning
  - generalization
raw_sources:
  - raw/sources/2021-10-generative-adversarial-training-for-neural-combinatorial-optimization-models.pdf
  - raw/sources/2021-10-generative-adversarial-training-for-neural-combinatorial-optimization-models.txt
paper.title: "Generative Adversarial Training for Neural Combinatorial Optimization Models"
paper.authors:
  - Anonymous authors (double-blind ICLR 2022 review)
paper.year: 2022
paper.venue: ICLR 2022 (under review, double-blind)
paper.arxiv: null
paper.doi: null
paper.code: null
classification.label: adversarial-training-for-nco
classification.task:
  - Traveling Salesman Problem (TSP)
  - Capacitated Vehicle Routing Problem (CVRP)
  - Orienteering Problem (OP)
  - Prize Collecting TSP (PCTSP)
  - 0-1 Knapsack Problem (KP)
classification.method_family: adversarial-training
classification.modality: routing/optimization
classification.datasets:
  - TSPLIB (100-1000 nodes)
  - CVRPLIB
classification.metrics:
  - Optimality gap (%)
  - Tour length / objective value
  - Inference time (seconds)
evidence_level: full-paper

## Citation

Anonymous authors. "Generative Adversarial Training for Neural Combinatorial Optimization Models." Under review at ICLR 2022 (double-blind).

## One-Sentence Contribution

提出 GANCO（Generative Adversarial Neural Combinatorial Optimization）框架，通过生成模型与优化模型的对抗式交替训练，提升神经组合优化（NCO）模型在训练分布外实例上的泛化能力。

## Problem Setting

组合优化问题（COPs）旨在从有限解空间中寻找最优解，许多重要的 COPs（如车辆路径问题）是 NP-hard 的。精确算法（如 branch-and-bound）在最坏情况下呈指数复杂度，难以应对中大规模问题。传统启发式方法依赖专家知识且开发周期长。

近年来，深度神经网络可以通过端到端方式学习启发式策略（如 Dai et al., 2017; Kool et al., 2019; Chen & Tian, 2019），在遵循训练分布的实例上表现良好。然而，当测试实例来自不同分布时，深度模型的泛化性能急剧下降——这一分布不匹配问题严重阻碍了学习型启发式的实际部署。

本论文针对的核心问题：如何提升 NCO 模型在未见分布上的泛化能力，同时保持其在原始训练分布上的性能。

## Method

### GANCO 框架概述

GANCO 是一个**模型无关**的通用框架，核心思想是部署一个额外的深度生成模型来产生对当前优化模型具有挑战性的训练实例。生成模型和优化模型以对抗方式交替训练：

1. **生成模型**（Generation Model）：以噪声为输入，通过自注意力网络输出节点属性的分布参数，采样生成实例。生成模型通过强化学习（REINFORCE 算法）训练，以最大化优化模型与传统非学习基线算法在生成实例上的性能差距。
2. **优化模型**（Optimization Model）：用原始训练方式，在基础训练分布和生成分布混合增强后的数据集上训练，以缩小性能差距。

### 生成模型架构

生成模型 $\Omega$ 以噪声输入 $h \in \mathbb{R}^{n \times 2}$（每个节点 2 维，独立采样自 $U(0,1)$）为输入，使用 AM 中的自注意力块（multi-head self-attention + 逐节点前馈层 + Batch Normalization + 跳跃连接），经 $k$ 个自注意力块编码，最后通过线性层 + sigmoid 激活输出分布参数 $\Omega(h) \in \mathbb{R}^{n \times d}$，其中 $d$ 为每个节点的属性数。实例从 $\mathcal{N}(\mu, \sigma^2)$ 中采样（$\mu = \Omega(h)$，$\sigma=0.05$ 固定），并缩放至有效范围。

### 生成模型训练

生成模型使用 REINFORCE 算法训练，损失函数最大化性能差距：$G(x, \Phi, B) = (O_\Phi(x) - O_B(x)) / O_B(x)$。

### 对抗训练流程

1. **预训练阶段**：在基础训练分布上训练优化模型至完全收敛。
2. **对抗训练阶段**（$N_a$ 次迭代）：
   - 随机重新初始化生成模型参数。
   - **生成训练**：REINFORCE 训练生成模型（最多 2000 迭代，batch size 100）。
   - **分布增强**：将生成的新分布加入分布池。
   - **优化训练**：混合数据训练优化模型（20 epoch，256000 实例/epoch），一半来自基础分布，一半来自生成分布。预训练后固定 AM 编码器仅训练解码器。

### 基线算法

TSP: Concorde | CVRP: HGS（快速版） | OP: Compass | PCTSP: ILS（快速版） | KP: DP

## Experiments

### 实验设置

- **基础模型**：AM（Kool et al., 2019），去除 BN 层并训练至完全收敛，性能优于原始 AM（TSP20/50/100 差距从 0.34%/1.76%/4.53% 降至 0.14%/0.73%/2.16%）。
- **超参数**：20 次对抗迭代，生成模型最多 2000 迭代，batch size 100，$\sigma=0.05$；优化模型 20 epoch，256000 实例/epoch。架构和优化器超参同 Kool et al. (2019)。
- **硬件**：RTX-2080Ti GPU；传统算法在 28 核 CPU 上 20 实例并行。
- **解码**：greedy | 10t | 100t。

### 测试分布

- **TSP**：Base（单位方形均匀）、Clustered（聚类）、Uniform（矩形随机宽高比）、Diagonal（对角线）、Gaussian（双变量高斯）、TSPLIB-S。
- **CVRP**：坐标分布同 TSP，需求有 Original/Small/Large/Identical/Quadrant/SL 六种，仓库位置 3 种。
- **KP**：将权重和价值视为 x/y 坐标，用 TSP 泛化分布，容量固定 12.5/25/25。
- **规模**：TSP/CVRP/OP/PCTSP n=20/50/100 各 10000 实例；KP n=50/100/200。

### 消融实验

去除 BN + 延长训练消融；遗传基 GB-AM 对比；多分布等比例训练 AM-T4 对比；跨问题生成 GANCO-AM-DIFF 对比。

## Results

### TSP 结果（greedy 解码）

| 分布 | n=20 AM gap | n=20 GANCO-AM gap | n=50 AM gap | n=50 GANCO-AM gap | n=100 AM gap | n=100 GANCO-AM gap |
|------|:-----------:|:-----------------:|:-----------:|:-----------------:|:------------:|:------------------:|
| Base | 0.14% | 0.14% | 0.73% | 0.83% | 2.16% | 2.28% |
| Cluster | 0.39% | **0.27%** | 3.07% | **2.04%** | 8.85% | **6.06%** |
| Uniform | 0.54% | **0.19%** | 3.37% | **1.45%** | 7.12% | **3.94%** |
| Diagonal | 2.29% | **0.29%** | 23.21% | **2.37%** | 61.47% | **7.39%** |
| Gaussian | 0.32% | **0.27%** | 4.86% | **1.96%** | 9.06% | **7.02%** |
| TSPLIB-S | 0.21% | **0.17%** | 1.77% | **1.26%** | 5.27% | **4.12%** |

**关键发现**：Diagonal n=100 上 AM 差距高达 61.47%，GANCO-AM 降至 **7.39%**（降 54.08pp）。10t/100t 采样平均差距从 16.52%/14.55% 降至 4.47%/3.48%。

### TSPLIB 基准

100-300 节点：AM 11.95% → GANCO-AM **7.05%**。300-1000 节点：AM 27.44% → GANCO-AM 23.37%。

### CVRP 结果（greedy, n=100）

| 分布 | AM gap | GANCO-AM gap |
|------|:-----:|:------------:|
| Base | 5.22% | 5.16% |
| Original | 7.25% | **6.18%** |
| Small | 21.80% | **14.65%** |
| Large | 7.02% | **6.20%** |
| Identical | 8.93% | **7.03%** |
| Quadrant | 9.40% | **7.76%** |
| SL | 12.06% | **9.51%** |

### KP 结果（greedy, n=200）

Cluster: AM 0.390% → GANCO-AM **0.184%** | Uniform: 0.174% → **0.140%** | Diagonal: 0.271% → **0.236%** | Gaussian: 0.191% → **0.143%** | TSPLIB-S: 0.233% → **0.151%**。

### POMO 结果

CVRP100 Small：POMO 单轨迹 40.74% → GANCO-POMO **7.82%**（降 32.92pp）。TSP100 Diagonal：POMO 21.78% → GANCO-POMO **2.12%**。

### 消融结果

- **GB-AM**（遗传基）：未改善泛化，Diagonal n=100 上 GB-AM 78.76% 甚至差于 AM 61.47%。
- **AM-T4**（多分布训练）：TSP100 Gaussian 上 AM-T4 6.27 差于 AM 6.21。
- **跨问题生成**：GANCO-AM-DIFF（20 迭代）得分 43.90，接近 GANCO-AM 的 44.00，优于 AM 的 41.02。

### 训练时间

GANCO-AM CVRP100 对抗训练 < **3 天**，AM 预训练就需 **14 天**。

## Limitations

1. 实验仅验证构造式启发模型（AM, POMO），未涉及改进式启发。
2. 仅在固定小规模（n ≤ 200）上训练测试，更大规模下改进幅度减小。
3. 依赖非学习基线算法的性能差距，基线可能成为瓶颈。
4. 每次对抗迭代重初始化生成模型增加计算开销。
5. 缺乏对抗训练的收敛性、泛化界或分布多样性理论分析。
6. 论文为双盲评审版本，代码未开放，结果不可复现。

## Reusable Claims

> **Claim**: GANCO 框架显著提升 NCO 模型分布外泛化，TSP Diagonal n=100 上差距从 61.47% 降至 7.39%。
> **Evidence**: Table 1, §4.1 | **Scope**: TSP, AM, greedy | **Confidence**: high

> **Claim**: GANCO 保持原始分布性能，Base 分布差距仅从 2.16% 升至 2.28%。
> **Evidence**: Table 1, §4.1 | **Scope**: 所有测试规模/分布 | **Confidence**: high

> **Claim**: 深度 RL 生成显著优于遗传基生成，GB-AM 未改善泛化性能。
> **Evidence**: Table 4 (Appendix A) | **Scope**: TSP 各分布 | **Confidence**: high

> **Claim**: GANCO 是模型无关的，可应用于 AM 和 POMO 两种 NCO 模型。
> **Evidence**: Table 3, Table 10 | **Scope**: TSP100, CVRP100 | **Confidence**: high

## Connections

- **Adversarial Training**: 类似 GAN（Goodfellow et al., 2014），但生成器目标为最大化性能差距而非生成不可区分数据。
- **UED**: 与 Dennis et al. (2020) 的对抗框架生成困难实例提升泛化异曲同工。
- **AM**: 基础优化模型（Kool et al., 2019）。
- **POMO**: 另一验证模型（Kwon et al., 2020）。
- **Instance Generation**: Liu et al. (2020) 用遗传算法生成实例，GANCO 扩展到深度 RL。
- **COPs benchmarking**: Concorde, HGS, LKH3, ILS, Compass 等传统求解器。

## Open Questions

1. GANCO 是否适用于改进式启发模型（LNS、2-opt 学习）？
2. n > 1000 时改进能否持续？
3. warm-start 生成模型是否优于从零重初始化？
4. 生成分布是否存在模式坍塌？
5. 对抗训练的泛化界理论分析？
6. 与持续学习结合在动态分布上自适应？

## Provenance

- **Raw source**: raw/sources/2021-10-generative-adversarial-training-for-neural-combinatorial-optimization-models.pdf
- **Extracted text**: raw/sources/2021-10-generative-adversarial-training-for-neural-combinatorial-optimization-models.txt
- **Evidence level**: full-paper
- **Extraction**: PyPDF2, 22 pages, 89051 chars, 2026-06-17
- **Status**: ICLR 2022 double-blind review, anonymous authors
- **Reproducibility**: Code planned but not available
<!-- openclaw:wiki:generated:end -->

## Related
<!-- openclaw:wiki:related:start -->
- No related pages yet.
<!-- openclaw:wiki:related:end -->
