---
pageType: synthesis
id: synthesis.how-to-craft-backdoors-with-unlabeled-data-alone
title: how-to-craft-backdoors-with-unlabeled-data-alone
sourceIds:
  - raw/sources/2024-How-to-Craft-Backdoors-with-Unlabeled-Data-Alone.pdf
status: active
updatedAt: 2026-06-17T03:04:03.793Z
---

# how-to-craft-backdoors-with-unlabeled-data-alone

## Notes
<!-- openclaw:human:start -->
<!-- openclaw:human:end -->

## Summary
<!-- openclaw:wiki:generated:start -->
---
title: "How to Craft Backdoors with Unlabeled Data Alone?"
type: paper
domain: ai-security
status: active
created: 2026-06-17
updated: 2026-06-17
tags:
  - backdoor-attack
  - self-supervised-learning
  - data-poisoning
  - no-label-backdoor
source_pages: []
raw_sources:
  - raw/sources/2024-How-to-Craft-Backdoors-with-Unlabeled-Data-Alone.pdf
  - raw/sources/How-to-Craft-Backdoors-with-Unlabeled-Data-Alone--full-text.txt
related_pages: []
paper:
  title: "How to Craft Backdoors with Unlabeled Data Alone?"
  authors: Anonymous authors
  year: 2024
  venue: ICLR 2024 (under review, double-blind)
classification:
  label: backdoor-attack
  task:
    - backdoor-attack
    - data-poisoning
  method_family:
    - no-label-backdoor
    - contrastive-selection
    - clustering-based-selection
  modality: vision
  datasets:
    - CIFAR-10
    - ImageNet-100
  metrics:
    - Clean Accuracy
    - Poison Accuracy
    - Attack Success Rate
    - Cluster Consistency Rate
evidence_level: full-paper

# How to Craft Backdoors with Unlabeled Data Alone?

## Citation

Anonymous authors. "How to Craft Backdoors with Unlabeled Data Alone?" Under review at ICLR 2024 (double-blind).

## One-Sentence Contribution

This paper proposes **no-label backdoors (NLB)**—a novel backdoor attack setting where the attacker only has access to unlabeled data—and introduces two poison selection strategies (clustering-based and contrastive selection) that achieve effective backdoor attacks on SSL models without any label information.

## Problem Setting

Prior backdoor attacks (dirty-label, clean-label) all require label information. The attacker has access to unlabeled dataset samples only (e.g., via unauthorized mirrors), has no labels and no domain expertise, yet aims to inject backdoors. Key challenge: selecting a class-consistent poison subset without labels. Random selection yields near-random ASR (~10% on CIFAR-10, ~1% on ImageNet-100).

## Method

**Clustering-based NLB (Sec 3.1):** Uses a pretrained SSL encoder + K-means to assign pseudo-labels, selects the smallest cluster ≥ poison budget M. Measures quality via Cluster Consistency Rate (CCR). Limitation: K-means is unstable across initializations (CCR varies ~20%–87%).

**Contrastive NLB (Sec 3.2):** Derives from a mutual information principle: optimal poison set maximizes I(X;S) between inputs and backdoor feature. Proposes Total Contrastive Similarity (TCS) criterion maximizing intra-poison similarity and minimizing poison-nonpoison similarity. Deterministic and more stable than clustering.

## Experiments

- **Datasets:** CIFAR-10 (50k images, 10 classes) and ImageNet-100 (100-class subset of ImageNet-1k). 9:1 pretrain/downstream split.
- **SSL methods:** SimCLR, MoCo v2, BYOL, Barlow Twins, all with ResNet-18 backbone.
- **Training:** 500 epochs (CIFAR-10) / 300 epochs (ImageNet-100) pretraining; 100/50 epochs linear probing.
- **Poison:** 6% (CIFAR-10) / 0.6% (ImageNet-100) rate, BadNet trigger (default), Blend trigger tested.
- **Baselines:** Random selection, label-aware backdoor (oracle).
- **Hardware:** Single RTX 3090 GPU, poisoning in 9.3s (clustering) / 10.2s (contrastive).

## Results

**Key results on CIFAR-10 (SimCLR):** Random ASR 14.93%; clustering ASR 98.80% (poison accuracy 11.02%); contrastive ASR 88.21% (poison accuracy 19.59%). Clean accuracy preserved (~86–87%).

**Key results on ImageNet-100 (SimCLR):** Random ASR 1.17%; clustering ASR 40.30% (poison accuracy 34.74%); contrastive ASR 74.46% (poison accuracy 19.34%).

Contrastive NLB outperforms clustering in most cases, gap <1% from label-aware oracle. Finetuning defense reduces but does not remove NLB (ASR 70.36–83.15% after finetuning on CIFAR-10). PatchSearch defense more effective but NLB still more resistant than label-aware methods.

## Limitations

1. K-means instability for clustering-based NLB.
2. Experiments limited to vision; NLP/audio not explored.
3. No pre-training dataset-level detection analysis.
4. Limited trigger types tested (BadNet, Blend).
5. No evaluation against stronger defenses (certified robustness, dataset sanitization).
6. Requires heuristic selection of cluster count K and poison budget M.

## Reusable Claims

1. No-label backdoors are feasible and effective without any label information (Tables 1-2).
2. Contrastive selection (MI-based) outperforms clustering-based selection on large-scale datasets (Table 2).
3. Random poison selection is ineffective for NLB (ASR ≈ random guess).
4. NLB is resistant to finetuning-based defense (Table 5).
5. NLB approaches oracle-level (label-aware) effectiveness (Table 3).
6. Mutual information provides a principled framework for poison selection (Section 3.2).

## Connections

Extends dirty-label (Gu et al., BadNets), clean-label (Turner et al.), and existing SSL backdoors (Saha et al., BadEncoder, Li et al.) that all require labels. Most restrictive setting: no external supervision at all. Related to Carlini & Terzis CLIP backdoor (requires multimodal data).

## Open Questions

1. Generalization to NLP/audio/multimodal modalities.
2. Adaptive trigger designs for NLB.
3. Pre-training dataset-level detection methods.
4. Minimum poison budget for effective NLB.
5. Scaling to massive datasets (Common Crawl, JFT-300M).

## Provenance

- Raw source: `raw/sources/2024-How-to-Craft-Backdoors-with-Unlabeled-Data-Alone.pdf`
- Full text: `raw/sources/How-to-Craft-Backdoors-with-Unlabeled-Data-Alone--full-text.txt`
- Extraction: PyPDF2, 17 pages, ~51k chars
- Evidence level: full-paper
- Ingested: 2026-06-17
<!-- openclaw:wiki:generated:end -->

## Related
<!-- openclaw:wiki:related:start -->
- No related pages yet.
<!-- openclaw:wiki:related:end -->
