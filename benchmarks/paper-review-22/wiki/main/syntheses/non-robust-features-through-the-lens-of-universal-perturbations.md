---
pageType: synthesis
id: synthesis.non-robust-features-through-the-lens-of-universal-perturbations
title: Non-Robust Features Through the Lens of Universal Perturbations
sourceIds:
  - raw/sources/2021-iclr-non-robust-features-universal-perturbations.pdf
status: active
updatedAt: 2026-06-17T03:07:17.173Z
---

# Non-Robust Features Through the Lens of Universal Perturbations

## Notes
<!-- openclaw:human:start -->
<!-- openclaw:human:end -->

## Summary
<!-- openclaw:wiki:generated:start -->
---
title: "Non-Robust Features Through the Lens of Universal Perturbations"
type: paper
domain: ai-security
status: active
created: 2026-06-17
updated: 2026-06-17
tags:
  - adversarial-examples
  - non-robust-features
  - universal-perturbations
  - adversarial-robustness
  - feature-analysis
source_pages: []
raw_sources:
  - raw/sources/2021-iclr-non-robust-features-universal-perturbations.pdf
  - raw/sources/2021-iclr-non-robust-features-universal-perturbations.txt
related_pages: []
paper:
  title: "Non-Robust Features Through the Lens of Universal Perturbations"
  authors: Anonymous authors
  year: 2021
  venue: ICLR 2021 (under review, double-blind)
classification:
  label: adversarial-robustness
  task:
    - adversarial-attack-analysis
    - feature-analysis
  method_family:
    - universal-adversarial-perturbations
    - non-robust-feature-analysis
    - scaling-analysis
  modality: vision
  datasets:
    - ImageNet-M10
    - CIFAR-10
  metrics:
    - Attack Success Rate
    - Test Accuracy
    - Transfer Success Rate
evidence_level: full-paper

# Non-Robust Features Through the Lens of Universal Perturbations

## Citation

Anonymous authors. "Non-Robust Features Through the Lens of Universal Perturbations." Under review at ICLR 2021 (double-blind).

## One-Sentence Contribution

This paper shows that universal adversarial perturbations leverage **human-aligned non-robust features** (semantically interpretable, spatially invariant) that are fundamentally different from standard adversarial non-robust features, but these human-aligned features carry substantially less predictive signal.

## Problem Setting

Prior work (Ilyas et al., 2019) established that adversarial examples exploit *non-robust features*—brittle features sensitive to small perturbations, believed to be unintelligible to humans yet useful for prediction. This explanation, however, lacks fine-grained understanding of what these features look like. The central question: **Are all non-robust features unintelligible to humans, or can some be human-aligned?** The paper uses *universal adversarial perturbations* (Moosavi-Dezfooli et al., 2017a)—single perturbation vectors that fool a model on many inputs—as a lens to isolate and study non-robust features that are more structured than standard adversarial perturbations.

**Definitions (Section 2):** A *useful feature* is a function positively correlated with the correct label in expectation. A *robustly useful feature* remains useful under adversarial perturbations within a set Δ. A *useful non-robust feature* is useful but not robustly useful. Universal perturbations δ are computed via PGD solving min_{δ∈Δ} E_{(x,y)~D} [L(f(x+δ), t)] over a *base set* of size K.

## Method

**1. Universal perturbation computation (Section 2.1):** Uses projected gradient descent (PGD) on cross-entropy loss with target class t, optimized over a base set of K images. Perturbations are `ℓ_p`-bounded (ℓ₂: ε=6.0, ℓ₁: ε=8/255 for ImageNet; ℓ₂: ε=1.0 for CIFAR-10). Hyperparameters: learning rate 2.0, batch size 128 or 256, up to 100 epochs (Appendix B.2.2).

**2. Local patch analysis (Section 3.1):** Randomly selects 64 local 80×80 patches from each universal perturbation, evaluates each patch's ASR in isolation, normalizes patch norms for ℓ₂ perturbations, and compares ASR to visual semantic content.

**3. Spatial invariance test (Section 3.2):** Measures ASR of translated perturbations (shifted by i pixels x-axis, j pixels y-axis, wraparound) over a subsampled grid with stride 4 pixels. Compares against standard adversarial perturbations on 256 test images from ImageNet-M10.

**4. Scaling analysis (Section 4):** Linearly scales universal perturbation δ by factor t (tδ), evaluates ASR on both natural and adversarially robust models. If robust leakage were significant, the robust model should react to amplified perturbations; if non-robust, only the natural model responds.

**5. Constructed dataset experiment (Section 5.1):** Following Ilyas et al. (2019), constructs datasets ̂D_univ and ̂D_adv where only universal non-robust features or standard non-robust features are predictive (by relabeling with perturbation target). Trains ResNet-18 models on these datasets and evaluates on original test set.

**6. Transferability analysis (Section 5.2):** Generates perturbations on source model (ResNet-18), measures probability of being classified as target class on target model (independent ResNet-18 or VGG16), considering only images misclassified by source.

**7. Universality interpolation (Section 5.3):** Varies base set size K from 1 (adversarial) to 256+ (fully universal) and measures generalization. Also tests class-universal and subclass-universal perturbations by restricting base set to single class or subclass.

## Experiments

### Datasets
- **ImageNet-M10** (Mixed10, Engstrom et al., 2019): 10 super-classes (Dog, Bird, Insect, Monkey, Car, Feline, Truck, Fruit, Fungus, Boat), each containing 6 ImageNet classes (60 subclasses total). Balanced subset of ImageNet ILSVRC2012.
- **CIFAR-10** (Krizhevsky et al., 2009): 10 classes, 50k training images. Used for additional results in appendices only.

### Models
- **Primary architecture:** ResNet-18 (He et al., 2016) for all main experiments.
- **Transfer experiments also use:** VGG16 (Simonyan & Zisserman, 2015) and independently initialized ResNet-18.
- **Robust models:** Trained with PGD (Madry et al., 2017), 3 steps, step size ⅔ε, ε=6.0 (ℓ₂) or ε=8/255 (ℓ₁).

### Model Accuracies (Table 7)
| Dataset | Model | Standard Test Acc (%) | Robust Test Acc (%) |
|---------|-------|----------------------|---------------------|
| ImageNet-M10 | Standard | 95.7 | <1.0 |
| ImageNet-M10 | ℓ₂ robust | 86.7 | 59.8 |
| ImageNet-M10 | ℓ₁ robust | 87.6 | 59.2 |
| CIFAR-10 | Standard | 94.8 | <1.0 |
| CIFAR-10 | ℓ₂ robust | 80.0 | 50.7 |

### Training Hyperparameters (Table 8)
- **Base models:** SGD with momentum, standard data augmentation, weight decay 5e-4.
- **Constructed dataset training:** Grid search over learning rates {0.01, 0.05, 0.1}, batch sizes {128, 256}, with/without LR drop by 10×. All models trained for 400 epochs with standard augmentation, weight decay 5×10⁻⁴.
- **Universal perturbation computation:** PGD, learning rate 2.0, batch size 128–256, up to 100 epochs.

### Evaluation Protocol
- **Metrics:** Attack Success Rate (ASR), Test Accuracy (generalization), Transfer Success Rate.
- **Robustness thresholds:** ℓ₂: ε=6.0, ℓ₁: ε=8/255 (ImageNet); ℓ₂: ε=1.0 (CIFAR-10).
- **Adversarial perturbations:** PGD, step size ε/3, 10 steps, no random restarts.

## Results

### Finding 1: Universal perturbations are more human-aligned (Section 3)

**Perceptual alignment:** Universal perturbations visually resemble their target class (e.g., dog face patterns for "dog" target, bird outlines for "bird" target), while standard adversarial perturbations at the same norm are unintelligible (Figures 1–2).

**Localized signal (Section 3.1):** Patches with highest ASR in universal perturbations correspond to the most semantically identifiable regions with the target class. For ℓ₂ perturbations on ImageNet-M10: highest-ASR patches achieve ASR up to 0.494 (dog) vs. lowest-ASR patches ~0.098 (near chance 10%). After norm normalization ≥ 0.136. For ℓ₁: highest-ASR patches up to 0.597 (dog, ℓ₁) vs. lowest ~0.101.

**Spatial invariance (Section 3.2):** Universal perturbations retain non-trivial ASR after translations of varying magnitudes. Standard adversarial perturbations drop to chance-level (~10%) ASR when shifted by >8 pixels. Universal perturbations remain effective across the full translation grid (Figure 4).

### Finding 2: Universal perturbations leverage non-robust features, not robust leakage (Section 4)

**Scaling analysis (Figure 5):** For universal perturbation (nat-univ-ptb, ℓ₂ norm ε=6.0, target bird):
- On natural model: ASR increases with scaling factor t, reaching ~0.9 at ℓ₂ norm ≈ 30.
- On robust model: ASR remains near 0 at all scales, showing no response.
- Control: universal perturbation computed on robust model (rob-univ-ptb, norm ε=30.0) does fool natural model.

Local patch scaling confirms: even the most semantic patches, when scaled, do not trigger the robust model (Figure 5b–c).

### Finding 3: Universal non-robust features carry less signal (Section 5)

**Generalization from constructed datasets (Table 3):**
| Dataset | Perturbation Set | Test Accuracy (%) |
|---------|-----------------|-------------------|
| ImageNet-M10 ℓ₂ | ̂D_adv | 74.5 |
| ImageNet-M10 ℓ₂ | ̂D_univ | 23.2 |
| ImageNet-M10 ℓ₁ | ̂D_adv | 78.7 |
| ImageNet-M10 ℓ₁ | ̂D_univ | 26.5 |
| CIFAR-10 ℓ₂ | ̂D_adv | 64.3 |
| CIFAR-10 ℓ₂ | ̂D_univ | 23.3 |

Universal non-robust features generalize at 23–26% vs. 64–79% for standard non-robust features—substantially lower, but well above chance (10%).

**Transferability (Figure 6):** Universal perturbations transfer much less than adversarial perturbations between models. ResNet-18→ResNet-18: adversarial transfer rate up to ~0.35 vs. universal ~0.10 for most classes. ResNet-18→VGG16: adversarial up to ~0.20 vs. universal ~0.05.

### Finding 4: Interpolating universality reveals trade-off (Section 5.3)

**Varying base set size K (Table 1):**
| K | Test Accuracy (%) |
|---|-------------------|
| 1 (adversarial) | 74.5 |
| 2 | 57.1 |
| 4 | 61.3 |
| 8 | 57.4 |
| 16 | 34.3 |
| 32 | 21.8 |
| 256 | 19.1 |

Generalization drops sharply even at small K (K=2: 57.1%). Semantic quality improves with K (at K≥64), suggesting a trade-off between semantic quality and generalizable signal.

**Varying source class (Table 2):** Random class 23.2% → single class 23.9% → single subclass 27.1%. Modest improvement, suggesting non-robust features are not strongly aligned with (sub)class divisions.

### Robust leakage bounds (Appendix A.3)
- Detuned dataset (cyclic shifted labels): 19.1% accuracy on original test set (< 26.5% from ̂D_univ, > 10% chance).
- Fixed-feature probing (Table 4): natural features 36.9%, natural diff init 35.0%, natural diff arch (VGG16) 26.4%, robust (ℓ₁) 22.3%. Residual signal not fully explained by leakage.

## Limitations

1. Experiments limited to vision (ImageNet-M10, CIFAR-10); no NLP or other modalities.
2. Only ResNet-18 used for main experiments; VGG16 for transfer control only.
3. No full ImageNet experiments for constructed datasets (computationally too expensive, as stated in Appendix A.2).
4. Theoretical model lacking—existing models (Tsipras et al., 2019; Allen-Zhu & Li, 2020) fail to distinguish between standard and universal perturbations (Section 5.3 Discussion).
5. Proposed trade-off between semantic quality and generalizable signal not fully resolved (Appendix A.5).
6. ℓ₁ vs ℓ₂ perturbation differences (non-linear patch interactions in ℓ₁) not fully explained (Appendix D).
7. Diversity of universal perturbations limited; requires fine-grained labels to increase diversity (Appendix F).
8. Double-blind submission—author identity and code availability unknown.

## Reusable Claims

1. **Some non-robust features are human-aligned** — Universal perturbations reveal non-robust features with semantic structure and spatial invariance (Sections 3, 4).
2. **Non-robust features are not monolithic** — Universal and standard adversarial perturbations leverage qualitatively different subsets of non-robust features (Sections 3 vs 5).
3. **Semantic quality trades off with generalizable signal** — More human-aligned non-robust features carry less predictive signal (Table 1, Section 5.3).
4. **Robust leakage is bounded** — Scaling analysis and bounded leakage experiments confirm universal perturbations primarily use non-robust features (Section 4, Appendix A.3).
5. **Universality interpolates non-robust signal** — Base set size K controls the trade-off between semantic alignment and signal strength (Table 1).
6. **Shared non-robust features decrease with semantic distance** — Toy model: perturbing over more images reduces intersection of shared non-robust features (Section 5.3 Discussion).

## Connections

- **Ilyas et al. (2019)** — Foundational work on non-robust features; this paper extends by showing non-robust features are not uniformly unintelligible.
- **Moosavi-Dezfooli et al. (2017a)** — Introduced universal adversarial perturbations; this paper uses them as analytical tool rather than attack.
- **Tsipras et al. (2019)** — Robustness vs accuracy trade-off; existing theoretical model fails to capture universality interpolation.
- **Geirhos et al. (2018); Yin et al. (2019); Xiao et al. (2020)** — Related work on texture bias, high-frequency features, and background signals that models exploit differently from humans.
- **Jetley et al. (2018)** — Also uses universal perturbation analysis to study class-specific patterns essential for classification.

## Open Questions

1. Can the remaining bulk of non-robust features (those not captured by universal perturbations) be further decomposed and characterized?
2. Is the trade-off between semantic quality and generalizable signal a universal property or specific to ℓ_p-constrained perturbations?
3. Can a precise theoretical model be developed that captures the interpolation phenomena observed with varying base set size K?
4. What explains the non-linear interaction between low-signal patches in ℓ₁ universal perturbations (Appendix D)?
5. Can diverse universal perturbations be recovered without fine-grained label information (Appendix F)?
6. Do these findings extend to other modalities (NLP, audio, graphs)?
7. What is the role of perturbation diversity in universal non-robust features and their human alignment?

## Provenance

- Raw source: `raw/sources/2021-iclr-non-robust-features-universal-perturbations.pdf`
- Full text: `raw/sources/2021-iclr-non-robust-features-universal-perturbations.txt`
- Extraction: PyPDF2, 22 pages, ~60k chars
- Evidence level: full-paper
- Ingested: 2026-06-17
<!-- openclaw:wiki:generated:end -->

## Related
<!-- openclaw:wiki:related:start -->
- No related pages yet.
<!-- openclaw:wiki:related:end -->
