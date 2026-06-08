# Semi-supervised Counting via Pixel-by-pixel Density Distribution Modelling

## Abstract
This paper focuses on semi-supervised crowd counting, where only a small portion of the training data are labeled. We formulate the pixel-wise density value to regress as a probability distribution, instead of a single deterministic value, and utilize a dual-branch structure to model the corresponding discrete form of the distribution function. On the basis, we propose a semi-supervised crowd counting model. Firstly, we enhance the transformer decoder by usingdensity tokens to specialize the forwards of decoders w.r.t. different density intervals; Secondly, we design a pixel-wise distribution matching loss to measure the differences in the pixel-wise density distributions between the prediction and the ground-truth; Thirdly, we propose an interleaving consistency regularization term to align the prediction of two branches and make them consistent. Extensive experiments on four datasets are performed to show that our method clearly outperforms the competitors by a large margin under various labeled ratio settings.

## Expert Reviewer Summary
(Summary unavailable; strengths provided as context)


- **Effective Noise Reduction through Density Classification:** Transforming the semi-supervised problem from regression to density classification is a reasonable approach for removing noise. The approach efficiently alleviates noise in traditional semi-supervised learning by transforming the density map regression task into a density-level classification task, enhancing the method's capability to manage noise and complexity.

- **Innovative Masking Strategy via Uncertainty:** The masking strat
