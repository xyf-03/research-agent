# How to Craft Backdoors with Unlabeled Data Alone?

## Abstract
(未能获取摘要)

## Expert Reviewer Summary
This paper explores a restrictive setting called no-label backdoors, where the attacker only has access to the unlabeled data alone, and so does the model trainer. The authors propose two strategies for poison selection: clustering-based selection using pseudolabels, and contrastive selection derived from the mutual information principle. In this setup, the unlabeled data is assigned “pseudolabels” by clustering algorithms such as K-means, using these pseudolabels for choosing samples to inject backdoor triggers. The mutual information strategy attempts to associate triggers with chosen samples to introduce an effective backdoor feature, generating poison sets that show high similarity within the set and low similarity with other samples. Experiments on systems trained with SSL methods like SimCLR, MoCo v2, BYOL, and Barlow Twins on CIFAR-10 and ImageNet-100 datasets indicate significant effectiveness of both approaches over random poisoning.
