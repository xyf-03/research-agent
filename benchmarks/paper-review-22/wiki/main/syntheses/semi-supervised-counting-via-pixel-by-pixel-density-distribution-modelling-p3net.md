---
pageType: synthesis
id: synthesis.semi-supervised-counting-via-pixel-by-pixel-density-distribution-modelling-p3net
title: semi-supervised-counting-via-pixel-by-pixel-density-distribution-modelling-p3net
sourceIds:
  - sources/2023-iclr-semi-supervised-counting-p3net.pdf
  - sources/2023-iclr-semi-supervised-counting-p3net.txt
status: active
updatedAt: 2026-06-17T03:15:20.218Z
---

# semi-supervised-counting-via-pixel-by-pixel-density-distribution-modelling-p3net

## Notes
<!-- openclaw:human:start -->
<!-- openclaw:human:end -->

## Summary
<!-- openclaw:wiki:generated:start -->
---
title: Semi-Supervised Counting via Pixel-by-Pixel Density Distribution Modelling (P3Net)
type: paper
domain: computer-vision
status: active
created: 2026-06-17
updated: 2026-06-17
tags:
  - crowd-counting
  - semi-supervised-learning
  - density-estimation
  - transformer
  - computer-vision
source_pages: []
raw_sources:
  - sources/2023-iclr-semi-supervised-counting-p3net.pdf
  - sources/2023-iclr-semi-supervised-counting-p3net.txt
paper.title: Semi-Supervised Counting via Pixel-by-Pixel Density Distribution Modelling
paper.authors: Anonymous authors (double-blind ICLR 2023 review)
paper.year: 2023
paper.venue: ICLR 2023 (under review)
paper.arxiv: null
paper.doi: null
paper.code: "Will be released (as stated in paper)"
classification.label: semi-supervised crowd counting
classification.task:
  - crowd counting
  - density estimation
classification.method_family: probabilistic density modelling with transformer decoder
classification.modality: RGB images
classification.datasets:
  - UCF-QNRF
  - JHU-Crowd++
  - ShanghaiTech A
  - ShanghaiTech B
classification.metrics:
  - MAE (Mean Absolute Error)
  - MSE (Mean Square Error)
evidence_level: full-paper
---

# Semi-Supervised Counting via Pixel-by-Pixel Density Distribution Modelling (P3Net)

## Citation

Anonymous authors. "Semi-Supervised Counting via Pixel-by-Pixel Density Distribution Modelling." ICLR 2023 (under review, double-blind).

## One-Sentence Contribution

提出 P3Net（Pixel-by-Pixel Probability distribution modelling Network），通过将像素级密度值建模为概率分布而非确定性值，结合密度 token 的 transformer decoder 和交错双分支自洽正则化，在仅使用少量标注数据的半监督人群计数任务上取得大幅性能提升。

## Problem Setting

半监督人群计数（semi-supervised crowd counting）问题：给定标注数据集 X（点标注的 ground truth 密度图）和未标注数据集 U（仅含人群图像），训练一个计数模型。通常 |U| ≫ |X|。标签比例常见设置为标注数据占总训练集的 5%、10% 和 40%。

传统方法存在两个主要挑战：
1. **标签不确定性**：标注中存在人头中心位置误差，导致监督信号噪声大；
2. **伪标签噪声**：未标注数据上的模型预测产生的伪标签普遍含噪。

现有半监督方法（L2R、GP、IRAST、SUA 等）采用自监督准则或伪标签生成来利用未标注数据，但其核心仍然依赖于像素级确定性密度值回归，在面对有限标签时鲁棒性差。

## Method

### 核心思想：密度值的概率分布建模

将每个像素的目标密度值建模为概率分布 p(x) 而非传统的 Dirac delta 确定性值 δ(x − d)。预测密度值通过期望计算：

**d = Σⱼ P(xⱼ) · xⱼ**

其中 {x₁, ..., x_C} 是将连续密度范围 [0, +∞) 量化为 C 个互斥区间后的离散表示。P(x) 通过 softmax 实现，将回归问题转化为密度区间分类问题。

### 三大模块

#### 1. Pixel-wise Distribution Matching (PDM) Loss

- 将标注的点转化为二维高斯平滑，得到每个像素的 one-hot 密度区间标签；
- 使用一维 Wasserstein 距离的离散闭式解来匹配预测分布和 ground-truth 分布；
- PDM loss = (Σⱼ (G(y, j) − G(p, j))²)^{1/2}，其中 G(·) 是累积分布函数；
- 相比 Cross Entropy 和 MSE，PDM 能区分"近偏差"和"远偏差"（例：标签 [0,1,0,0] 时，预测 [0.2,0.3,0.5,0] 优于 [0.2,0.3,0,0.5]）；
- 与 DM-Count 的区别：DM-Count 在空间域做最优传输，PDM 在密度区间维度做分布匹配。

#### 2. Transformer 密度 Token 专业化

- 引入 C 个可学习的 density token（嵌入向量），每个 token 编码特定密度区间的语义信息，其中第一个 token 专门处理背景区域 [0, b₁)；
- 通过 transformer decoder 的 cross-attention：C(T, F) = Softmax((TW_Q)(FW_K)^T / √Z)(FW_V)，使得每个 token 关注特征图中对应密度区间的区域；
- 输出通过 softmax 沿类别维度得到 C 张预测分布图，每张图代表一个密度区间在全图各 patch 的分布；
- 与 DETR 的区别：DETR 的 query 是可交换的且需要匈牙利匹配，P3Net 的 density token 与密度区间一一绑定，语义明确，不需要匹配。

#### 3. 交错双分支与 Inter-branch Expectation Consistency Regularization (ECR)

- **交错双分支结构**：两个并行分类任务具有交叠的密度区间边界（interleaving quantization），同一像素在边界附近落入一个分支的边界时，在另一分支中更容易被正确分类；
- **软量化级别分配**：推理时保留预测概率分布，用期望值代替硬最大分类，降低量化误差；两分支的最终密度通过置信度加权融合：d = ω·p·v₁^T + (1−ω)·q·v₂^T，其中 ω = ‖p‖∞ / (‖p‖∞ + ‖q‖∞)；
- **ECR 自监督项**：对未标注数据，强制两分支的密度期望一致 ℒ_E = ‖E ∘ R‖²₂，R = v₁O₁ − v₂O₂，E 为动态掩码仅在两分支置信度均高于阈值 ξ=0.5 时激活；
- **总损失**：ℒ = ℒ_P + λℒ_E，λ=0.01。

## Experiments

### 数据集

| 数据集 | 图像数 | 标注点 | train/test split |
|--------|--------|--------|-----------------|
| UCF-QNRF | 1,535 (高清) | 125万 | 1,201 / 334 |
| JHU-Crowd++ | 4,372 | 151万 | 2,272 / 500(val) / 1,600 |
| ShanghaiTech A | 482 | 244,167 | 300 / 182 |
| ShanghaiTech B | 716 | 88,488 | 400 / 316 |

### 训练设置

- **Backbone**：VGG-19（ImageNet 预训练）
- **优化器**：Adam，lr=1e-5
- **Decoder 层数**：4
- **密度区间数 C**：25
- **损失参数**：λ=0.01, ξ=0.5
- **数据增强**：水平翻转、随机缩放 [0.7, 1.3]、随机裁剪 512×512（ShanghaiTech A 为 256×256）
- **图像缩放**：短边限制在 2048 像素内
- **硬件**：单张 RTX 3080

### 评估协议

- **指标**：MAE（Mean Absolute Error）和 MSE（Mean Square Error）
- **标签比例设定**：5%、10%、40%（40% 对应 Meng et al. ICCV 2021 的 50% 设定，因其中 10% 用作验证集）

### 消融实验

1. **ECR 效果**（UCF-QNRF）：仅用 ℒ_P 为 5%/10%/40%/100%，加 ℒ_E 后 MAE 分别从 129.5→115.3、117.4→103.4、97.8→90.0、78.5→（fully supervised 无 ECR）。MAE 改善 7.8-14.2，MSE 改善 12.2-32.8。
2. **PDM vs CE vs MSE 分类损失**（UCF-QNRF 5%）：PDM 115.3 MAE 优于 CE 125.4 和 MSE 132.8。PDM 195.2 MSE 优于 CE 211.6 和 MSE 223.2。
3. **PDM vs BL vs DM 计数损失**（UCF-QNRF 5%）：PDM 115.3/195.2 优于 BL 136.5/234.7 和 DM-Count 133.4/225.3。
4. **概率分布建模效果**（UCF-QNRF）：L⁻_P（硬最大+简单平均）5% MAE 134.5/240.6 vs ℒ_P 129.5/212.8；100% L⁻_P 85.8/142.7 vs ℒ_P 78.5/135.8。概率分布建模和期望融合带来显著提升。

## Results

### 与 SOTA 对比（Table 1）

**UCF-QNRF**

| 方法 | 5% MAE | 5% MSE | 10% MAE | 10% MSE | 40% MAE | 40% MSE |
|------|--------|--------|---------|---------|---------|---------|
| MT | 172.4 | 284.9 | 156.1 | 250.3 | 147.2 | 249.6 |
| L2R | 160.1 | 272.3 | 148.9 | 249.8 | 145.1 | 256.1 |
| GP | 160.0 | 275.0 | - | - | 136.0 | - |
| IRAST | - | - | - | - | 138.9 | - |
| SUA | - | - | - | - | 130.3 | 226.3 |
| **P3Net (Ours)** | **115.3** | **195.2** | **103.4** | **179.0** | **90.0** | **155.4** |

相比第二优方法，P3Net 在 5% 设定下 MAE 降低 **44.7**（QNRF）；3 种标签比例下 MAE 平均降低约 **28.9%**（40% 设定）/ **23.5%**（10% 设定）/ **22.0%**（5% 设定）。

**JHU-Crowd++**

| 方法 | 5% MAE | 5% MSE | 10% MAE | 10% MSE | 40% MAE | 40% MSE |
|------|--------|--------|---------|---------|---------|---------|
| MT | 101.5 | 363.5 | 90.2 | 319.3 | 121.5 | 388.9 |
| L2R | 101.4 | 338.8 | 87.5 | 315.3 | 123.6 | 376.1 |
| SUA | - | - | - | - | 80.7 | 290.8 |
| **P3Net (Ours)** | **80.8** | **306.1** | **71.8** | **294.4** | **58.9** | **251.9** |

**ShanghaiTech A**

| 方法 | 5% MAE | 5% MSE | 10% MAE | 10% MSE | 40% MAE | 40% MSE |
|------|--------|--------|---------|---------|---------|---------|
| MT | 104.7 | 156.9 | 94.5 | 153.5 | 88.2 | 151.1 |
| L2R | 103.0 | 155.4 | 90.3 | 153.5 | 86.5 | 148.2 |
| GP | 102.0 | 172.0 | - | - | 89.0 | - |
| AL-AC | - | - | 87.9 | 139.5 | - | - |
| IRAST | - | - | 86.9 | 148.9 | - | - |
| IRAST+SPN | - | - | 83.9 | 140.1 | - | - |
| SUA | - | - | - | - | 68.5 | 121.9 |
| **P3Net (Ours)** | **85.5** | **131.0** | **72.1** | **116.4** | **63.0** | **100.9** |

**ShanghaiTech B**

| 方法 | 5% MAE | 5% MSE | 10% MAE | 10% MSE | 40% MAE | 40% MSE |
|------|--------|--------|---------|---------|---------|---------|
| MT | 19.3 | 33.2 | 15.6 | 24.5 | 15.9 | 25.7 |
| L2R | 20.3 | 27.6 | 15.6 | 24.4 | 16.8 | 25.1 |
| GP | 15.7 | 27.9 | - | - | - | - |
| AL-AC | - | - | 13.9 | 26.2 | - | - |
| IRAST | - | - | 14.7 | 22.9 | - | - |
| SUA | - | - | - | - | 14.1 | 20.6 |
| **P3Net (Ours)** | **12.0** | **22.0** | **10.1** | **18.2** | **7.1** | **12.0** |

### 全监督设定（UCF-QNRF）
P3Net 在全监督（100% 标签）下取得 78.5 MAE，进一步验证了方法的有效性。

## Limitations

1. **ECR 无法消除确认偏差（confirmation bias）**：自监督一致性正则化可以缓解但无法完全消除模型自身错误的累积。
2. **复杂背景/极端拥挤场景性能下降**：当图像背景过于复杂或密度过高时，模型可能产生较差的结果。
3. **依赖预定义密度区间**：C=25 和区间边界需要根据数据集先验知识（或参照 Wang et al. 2021a 的方法）设定，缺乏自适应机制。
4. **推理复杂度**：双分支结构和 transformer decoder 比传统单分支 CNN 方法计算开销更大（原文未提供具体 FPS）。

## Reusable Claims

- **Claim 1**: 将像素级密度值建模为概率分布（而非确定性狄拉克 delta）能有效提升半监督人群计数的鲁棒性。
  - Evidence: Table 4, UCF-QNRF, L⁻_P vs ℒ_P，5% MAE 134.5→129.5，100% MAE 85.8→78.5。
  - Scope: 人群计数，半监督/全监督，VGG-19 backbone。
  - Confidence: high。

- **Claim 2**: PDM Loss（基于一维 Wasserstein 距离的分布匹配损失）优于 CE 和 MSE 损失。
  - Evidence: Table 3, UCF-QNRF 5%，PDM 115.3/195.2 vs CE 125.4/211.6 vs MSE 132.8/223.2。
  - Scope: 半监督人群计数，5% 标签比例。
  - Confidence: high。

- **Claim 3**: 密度 token（density tokens）通过 transformer decoder cross-attention 专业化处理不同密度区间特征，优于传统 DETR 式可交换 query 设计。
  - Evidence: 论文 Section 3.2 定性分析及整体 SOTA 结果间接验证（无直接消融实验排除 tokens）。
  - Scope: 人群计数密度估计。
  - Confidence: medium。

- **Claim 4**: Inter-branch Expectation Consistency Regularization (ECR) 通过交错双分支的期望一致性自监督有效提升未标注数据的利用效率。
  - Evidence: Table 2, UCF-QNRF，5% MAE 129.5→115.3（−14.2），10% 117.4→103.4（−14.0），40% 97.8→90.0（−7.8）。
  - Scope: 半监督人群计数，所有标签比例。
  - Confidence: high。

## Connections

- **CSRNet (Li et al. 2018)**：使用空洞卷积扩大感受野；P3Net 改用 transformer decoder 进行跨区域关联，突破局部感受野限制。
- **DM-Count (Wang et al. 2020)**：在空间域做最优传输分布匹配；P3Net 的 PDM loss 在密度区间维度做分布匹配。
- **DETR (Carion et al. 2020)**：引入 transformer decoder 和可学习 query；P3Net 使用 density token 绑定密度区间，消除匈牙利匹配需求。
- **UEPNet (Wang et al. 2021a)**：使用交错双分支结构处理计数区间划分；P3Net 在此基础上引入概率分布建模和期望一致性自监督。
- **Mean Teacher (Tarvainen & Valpola 2017)**：一致性正则化；P3Net 使用双分支间的期望一致性代替 teacher-student 一致性。
- **L2R (Liu et al. 2018b)**：通过排序任务自监督利用未标注数据；P3Net 通过 ECR 期望一致性利用未标注数据。

## Open Questions

1. ECR 的阈值 ξ=0.5 是否最优？有无自适应阈值策略？
2. 密度区间数量 C 和边界划分策略对性能的敏感性有多大？
3. P3Net 的框架是否可推广到其他密集估计任务（如目标检测的密集回归、深度估计）？
4. 代码未公开，部分关键结果（如 FPS、模型参数量、NWPU-Crowd 结果）仅提及附录但不可验证。
5. 双分支设计是否可通过权重共享减少参数量而不牺牲性能？

## Provenance

- **PDF 源文件**: sources/2023-iclr-semi-supervised-counting-p3net.pdf (1.7 MB, 12 pages, ICLR 2023 double-blind submission)
- **全文提取**: sources/2023-iclr-semi-supervised-counting-p3net.txt (48,113 chars, extracted via PyPDF2)
- **提取日期**: 2026-06-17
- **提取完整性**: 全文 12 页全部提取，包含 Section 1-5、References、Tables 1-4、Figures 1-2
- **缺失内容**: Appendix（包含 NWPU-Crowd 实验和全监督细节）原文引用但不在 12 页主文中，无法提取
- **Evidence Level**: full-paper — 全文精读，可用部分覆盖所有主要 claims
- **审核说明**: 本文为 double-blind 投稿版本，作者匿名，代码标注"will be released"但截止入库时未公开，无法验证结果
<!-- openclaw:wiki:generated:end -->

## Related
<!-- openclaw:wiki:related:start -->
- No related pages yet.
<!-- openclaw:wiki:related:end -->
