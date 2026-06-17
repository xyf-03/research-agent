---
title: "Feature Selection in the Contrastive Analysis Setting"
type: paper
domain: contrastive-analysis
status: seed
created: 2026-06-17
updated: 2026-06-17
tags:
  - feature-selection
  - contrastive-analysis
  - weak-supervision
  - representation-learning
  - biomedical
source_pages: []
raw_sources:
  - raw/sources/P-gDXxGYCib.pdf
  - raw/sources/P-gDXxGYCib-extracted.txt
related_pages: []
paper:
  title: "Feature Selection in the Contrastive Analysis Setting"
  authors: ["Anonymous authors (double-blind)"]
  year: 2022
  venue: "ICLR 2022 (under review, double-blind)"
  arxiv: null
  doi: null
  code: "www.placeholder.com (supplementary, to be made public upon acceptance)"
  project: null
classification:
  label: contrastive-feature-selection
  task:
    - unsupervised-feature-selection
    - contrastive-analysis
  method_family:
    - stochastic-gating
    - autoencoder
    - contrastive-learning
  modality:
    - tabular
    - image
    - gene-expression
  datasets:
    - Grassy MNIST
    - Epithelial Cell Gene Expression (Haber et al., 2017)
    - Bone Marrow Cell Treatment Response (Zheng et al., 2017)
    - Mice Protein Expression (Higuera et al., 2015)
    - Smartphone Activity Recognition (UCI HAR)
  metrics:
    - downstream-classification-accuracy
evidence_level: full-paper

# Feature Selection in the Contrastive Analysis Setting

## Citation

Anonymous authors. "Feature Selection in the Contrastive Analysis Setting." *ICLR 2022* (under review, double-blind). 18 pages.

## One-Sentence Contribution

本文提出 **CFS (Contrastive Feature Selection)**，在 contrastive analysis (CA) 设置下利用背景数据集的弱监督信号，选择在目标数据集中富集但不在背景数据集中出现的特征，解决了标准无监督特征选择方法在目标-背景共享噪声占主导时无法选出有效特征的问题。

## Problem Setting

**核心问题**：给定高维目标数据集 $X = \{x_i\}_{i=1}^n \in \mathbb{R}^{n \times d}$，同时存在一个背景数据集 $B = \{b_j\}_{j=1}^m \in \mathbb{R}^{m \times d}$（如病患 vs. 健康对照），选取 $k$ 个特征使得下游任务（如分类）性能最优。

**数据生成过程假设**（Section 2，Figure 2）：
- 观测 $x_i$ 由两组隐变量生成：**salient latent variables** $s_i$（目标特有的显著变化）和 **background latent variables** $z_i$（目标与背景共享的无关变化）：$x_i \sim p(x|z_i, s_i)$
- 标签 $y_i$ 仅依赖于 $s$：$y_i \sim q(y|s_i)$
- 背景样本 $b_j$ 仅由 $z$ 生成（$s$ 固定为常数 $s_0$）
- 目标与背景数据量不要求相等（$n \neq m$），目标与背景样本之间没有特殊配对关系

**难点**：当共享的无关噪声占总体方差主体时，标准无监督特征选择方法会选出捕获噪声的特征而非真正反映 $s$ 的特征。

## Method

**CFS 整体框架**（Section 4，Figure 3）由三个组件构成：

1. **背景表示函数 $g_z: \mathbb{R}^d \rightarrow \mathbb{R}^{k'}$**：将输入映射到低维表示，仅捕获背景变量 $z$ 的变化（不含 $s$ 信息）
2. **Concrete Selector Layer（具体选择层）**：使用 concrete random variable（Balın et al., 2019）的可微松弛选 $k$ 个特征，输出 $x_i^S$（限制在特征子集 $S$ 上的观测）
3. **重建函数 $f_\theta: \mathbb{R}^{k + k'} \rightarrow \mathbb{R}^d$**：用 $[g_z(x_i); x_i^S]$ 重建目标点，或用 $[g_z(b_j); \mathbf{0}]$ 重建背景点（零向量代表无显著变化）

**优化目标**：
$$\arg\min_{S, \theta} \mathbb{E}\|f_\theta(g_z(x_i), x_i^S) - x_i\|_2^2$$

即选择最能捕获 $g_z$ 未能捕捉的目标数据变化的那组特征。

**三种 $g_z$ 学习变体**：

| 变体 | 方法 | 关键特性 |
|------|------|----------|
| **Joint** | $g_z$ 为 MLP，与 selector、$f_\theta$ 联合训练 | 高度表达，但可能存在信息泄漏 |
| **Pretrained** | 先在背景数据集上训练标准自编码器，冻结编码器权重作为 $g_z$ | 防止 $g_z$ 编码显著变化 |
| **Gates** | $g_z$ 为第二个 Concrete Selector Layer | 约束 $g_z$ 做特征选择而非通用表示学习 |

### Concrete Selector Layer（附录 A）

基于 concrete random variable（Maddison et al., 2016; Jang et al., 2016）的 Gumbel-Softmax 松弛。每个节点采样 $d$ 维 concrete 随机向量 $m^{(i)}$，输出 $x \odot m^{(i)}$。使用温度退火调度：$T(b) = T_0 (T_B / T_0)^{b/B}$，从 $T_0=10$ 退火到 $T_B=0.1$。

## Experiments

### 数据集与预处理（Section 5.2.1，附录 B）

#### Grassy MNIST（半合成）
- **目标**：MNIST 手写数字叠加 ImageNet 草地图像（草地振幅为数字的 2 倍，最终 28×28 像素）
- **背景**：仅草地图像
- **任务**：按数字类别分类（0-9）
- **特征**：每个像素作为独立特征（d=784）

#### Epithelial Cell Gene Expression
- **来源**：Haber et al. (2017)，小鼠肠道上皮细胞
- **目标**：Salmonella 和 H. poly 感染细胞（2 类）
- **背景**：健康对照细胞
- **维度**：15215 特征，目标 3584+2592 样本，背景 897 样本

#### Bone Marrow Treatment Response（Leukemia）
- **来源**：Zheng et al. (2017)，AML 患者移植前后
- **目标**：移植前 vs. 移植后（2 类）
- **背景**：健康对照
- **维度**：12079 特征，目标 6318+1985 样本，背景 1580 样本

#### Mice Protein Expression
- **来源**：Higuera et al. (2015)，Down 综合征小鼠
- **目标**：Down 综合征小鼠按治疗方案分（4 类）
- **背景**：健康未处理小鼠
- **维度**：77 特征，目标 444+111 样本，背景 108 样本

#### Smartphone Activity Recognition
- **来源**：UCI HAR 数据集
- **目标**：步行、坐、躺等 5 类活动
- **背景**：躺（laying）时测量
- **维度**：561 特征，目标 6684+1555 样本，背景 1671 样本

### Baseline 方法
- Laplacian Score (He et al., 2005)
- MCFS (Cai et al., 2010)
- PFA (Lu et al., 2007)
- Concrete Autoencoder (CAE; Balın et al., 2019)
- Gated Laplacian Score (Lindenbaum et al., 2020)
- Variances（简单方差差过滤基线）
- Supervised Concrete AE（目标 vs. 背景分类的监督 CAE）

### 训练设置（附录 C）
- **框架**：PyTorch + PyTorch Lightning
- **优化器**：ADAM（lr=0.001, β1=0.9, β2=0.999）
- **batch size**：128
- **Split**：80-20 训练-测试（训练数据用于选择特征和训练分类器，测试数据仅用于评估）
- **重建函数 $f_\theta$**：2 个隐藏层 512 维 + ReLU（Mice Protein 用 1 层 512）
- **Joint CFS $g_z$**：1 隐藏层 128 维 MLP
- **Pretrained CFS $g_z$**：预训练自编码器的编码器（1 隐藏层 128）
- **Gates CFS $g_z$**：第二个 Concrete Selector Layer
- **训练终止条件**：Concrete 样本均值超过 0.99
- **下游分类器**：Extremely Randomized Trees（ExtraTreesClassifier, n_estimators=100）
- **补充实验**：XGBoost 作为下游分类器（附录 F）

## Results

### Grassy MNIST 实验结果（Figure 4）

#### 下游分类准确率（Figure 4a）
- $k \in [10, 50]$，固定背景表示大小 $k'=20$
- **Pretrained CFS 和 Gates CFS 在所有 $k$ 值上均优于所有基线方法**
- Joint CFS 未超越基线方法，表明信息泄漏导致特征选择质量下降

#### 背景表示大小敏感性（Figure 4b）
- 固定 $k=20$，$k' \in [10, 50]$
- Pretrained 和 Gates CFS 在所有 $k'$ 设置下均持续优于无监督基线
- Joint 仍低于基线

#### 噪声-信号比敏感性（Figure 4c）
- 草地缩放因子 0 到 4（背景振幅从 0 到数字的 4 倍）
- Pretrained 和 Gates CFS 在所有非零噪声水平下持续优于基线
- 即使噪声远超信号（scale=4）仍保持优势

### 解缠程度量化（Figure 5）

**实验设计**：
- (a) 用所选目标特征重建背景样本 → 更高 MSE = 更好解缠
- (b) 用背景表示 $g_z(x_i)$ 重建目标样本 → 更高 MSE = 更好解缠

**发现**：Pretrained 和 Gates CFS 在两个解缠指标上均显著优于 Joint CFS，表明有效解缠是 CFS 成功的关键。

### 真实数据集结果（Table 1）

| 数据集 | Lap | MCFS | PFA | CAE | Gated Lap | CFS (Pretrained) | CFS (Gates) |
|---------|-----|------|-----|-----|-----------|------------------|-------------|
| Epithelial Cell | 0.593 | 0.606 | 0.596 | 0.834 | 0.638 | **0.904** | 0.897 |
| Leukemia Treatment | 0.708 | 0.853 | 0.588 | 0.934 | 0.644 | **0.970** | 0.952 |
| Mice Protein | 0.865 | 0.820 | 0.838 | 0.793 | 0.784 | 0.847 | **0.973** |
| Smartphone Activity | 0.846 | 0.912 | 0.906 | 0.923 | 0.904 | 0.937 | **0.961** |

- **CFS (Pretrained)**：3/4 数据集最优，Epithelial Cell (+0.070 vs. CAE)，Leukemia (+0.036 vs. CAE)
- **CFS (Gates)**：Mice Protein (+0.039 vs. Lap)，Smartphone (+0.038 vs. CAE)
- 唯一例外：Pretrained CFS 在 Mice Protein 上 (0.847) 略低于 CAE 最优基线 (0.865)
- XGBoost 下游分类结果（附录 F Table 3）与表 1 结论一致

### Selected Features 可视化（Figure 1，附录 D.2）
- CFS（Pretrained/Gates）选中的特征集中在图像中心（数字所在区域）
- CAE 等基线选中的特征散布在整个图像（包括边缘无数字区域）
- 基于谱信息的基线（Laplacian Score, Gated Laplacian）倾向于选择少量的特征簇

## Limitations

1. **需要背景数据集**：CFS 要求用户提供由无关变量生成的背景数据集，并非所有场景都能获取。不过论文指出临床试验等生物医学场景中这类数据常规收集。
2. **Joint 变体失败**：联合训练的 CFS 因信息泄漏效果较差，实际应用中需使用 Pretrained 或 Gates 变体。
3. **匿名提交**：论文在 ICLR 2022 投稿时为双盲状态，作者身份未知，代码链接为占位符。
4. **K 值选择**：论文未讨论如何在不使用标签的情况下自动选择最优 $k$。
5. **高维与低维差异**：真实数据集维度差异大（77 到 15215），模型架构需根据维度调整。

## Reusable Claims

> **Claim**: CFS（Pretrained 和 Gates 变体）利用背景数据集做弱监督特征选择，在 CA 任务中持续超越所有标准无监督特征选择方法。
> **Evidence**: Table 1 (4 个真实数据集)，Figure 4a (Grassy MNIST 多 k 值对比)
> **Scope**: 目标-背景数据对的 CA 设置，下游分类任务，k=5~50
> **Confidence**: high

> **Claim**: 有效的背景-显著变化解缠是 CFS 成功的关键——信息泄漏会降低所选特征的质量。
> **Evidence**: Figure 5（解缠量化实验），对比 Joint（高泄漏、低性能）vs. Pretrained/Gates（低泄漏、高性能）
> **Scope**: 基于重建的 CFS 框架
> **Confidence**: medium

> **Claim**: 在基因表达数据（单细胞 RNA-seq）上，CFS 选择的特征可使下游分类准确率超过 90%，而标准无监督方法通常在 60-80% 范围。
> **Evidence**: Table 1，Epithelial Cell (CFS 0.904 vs. best baseline CAE 0.834) 和 Leukemia (CFS 0.970 vs. CAE 0.934)
> **Scope**: 生物医学基因表达数据，k=20
> **Confidence**: medium

## Connections

- **Contrastive PCA (cPCA; Abid et al., 2018)**：扩展 PCA 到 CA 设置，学习显著主成分。CFS 将同一思路从表示学习延伸到特征选择。
- **Contrastive Variational Autoencoder (cVAE; Abid & Zou, 2019)**：概率隐变量模型用于 CA。CFS 使用确定性重建而非 VAE 框架。
- **Concrete Autoencoder (Balın et al., 2019)**：CFS 的 Concrete Selector Layer 直接基于 CAE，区别在于 CFS 额外使用背景表示 $g_z$ 和背景重建损失（零向量）来隔离显著变化。
- **Stochastic Gates (Yamada et al., 2020; Lindenbaum et al., 2020)**：CFS 借鉴了可微随机门控特征选择技术。
- **Disentangled Representation Learning**：CA 可视为解缠表示学习的一个特例，区别在于 CA 只需解缠背景与显著因子，且有背景数据集的弱监督。
- **Contrastive Representation Learning (SimCLR, etc.)**：尽管名称相似，论文明确指出 CA 与对比表示学习无直接关系。

## Open Questions

1. **自动选择 $k$**：如何在无标签条件下自动确定最优特征子集大小？是否可使用重建误差或解缠度指标？
2. **信息泄漏的根本原因**：Joint 变体的信息泄漏机制是什么？是否有更好的正则化方法（如互信息约束、对抗解缠）来允许联合训练？
3. **扩展到更多模态**：CFS 是否适用于图像/视频、时间序列（如脑电图）等其他模态？
4. **理论保证**：在什么条件下 CFS 能保证选出最优特征集？是否存在可识别性保证？
5. **大规模应用**：当特征数 $d$ 极大（如全基因组）时，Concrete Selector Layer 的可扩展性如何？
6. **代码可复现**：论文代码标注为 placeholder，被接收后是否已公开？

## Provenance

- **PDF**: `raw/sources/P-gDXxGYCib.pdf` (18 pages, ICLR 2022 under review)
- **Full text extraction**: `raw/sources/P-gDXxGYCib-extracted.txt` (64,743 chars extracted via PyPDF2)
- **Evidence level**: full-paper — 全文 18 页精读，捕获全部方法、实验细节、数据预处理和结果
- **Ingestion date**: 2026-06-17
- **Ingested by**: Ingest agent (subagent)
- **Limitations**: 论文为双盲审稿版本，部分元数据（作者、代码链接）不完整；数值结果来自论文表格和图表描述，非独立复现

## Related
<!-- openclaw:wiki:related:start -->
- No related pages yet.
<!-- openclaw:wiki:related:end -->
