# Personalized Subgraph Federated Learning with Differentiable Auxiliary Projections

**Wei Zhuo, Zhaohuan Zhan, Han Yu**

Nanyang Technological University, Shenzhen MSU-BIT University

*Total: 31 pages*

---

## Page 1

Personalized Subgraph Federated Learning with
Differentiable Auxiliary Projections
Wei Zhuo1, Zhaohuan Zhan2, Han Yu1
1Nanyang Technological University,2Shenzhen MSU-BIT University
1{wei.zhuo, han.yu}@ntu.edu.sg,2zhan.z@smbu.edu.cn
Abstract
Federated Learning (FL) on graph-structured data typically faces non-IID chal-
lenges, particularly in scenarios where each client holds a distinct subgraph sampled
from a global graph. In this paper, we introduceFederated learning withAuxiliary
projections ( FedAux ), a personalized subgraph FL framework that learns to align,
compare, and aggregate heterogeneously distributed local models without sharing
raw data or node embeddings. In FedAux , each client jointly trains (i) a local
GNN and (ii) a learnable auxiliary projection vector ( APV) that differentiably
projects node embeddings onto a 1D space. A soft-sorting operation followed by a
lightweight 1D convolution refines these embeddings in the ordered space, enabling
theAPVto effectively capture client-specific information. After local training, these
APVs serve as compact signatures that the server uses to compute inter -client simi-
larities and perform similarity -weighted parameter mixing, yielding personalized
models while preserving cross -client knowledge transfer. Moreover, we provide rig-
orous theoretical analysis to establish the convergence and rationality of our design.
Empirical evaluations across diverse graph benchmarks demonstrate that FedAux
substantially outperforms existing baselines in both accuracy and personalization
performance. The code is available at https://github.com/JhuoW/FedAux.
1 Introduction
Real-world data often manifests as relational structures, ranging from social interactions [ 30,46]
and financial networks [ 28,45] to molecular graphs [ 35,44], whose scale and privacy constraints
increasingly require training to be carried out in a federated manner [ 9], whereby multiple clients
collaboratively learn a Graph Neural Network (GNN) model without exchanging their raw data.
However, applying federated learning to graph-structured data, such as social networks, faces severe
challenges due tonon-identically and independently distributed(non-IID) data across clients. For
example, consider a federated learning scenario involving multiple regional social networking
platforms, each representing a distinct subgraph of a global social network. Users within each region
exhibit unique interaction patterns and distinct interests, resulting in significant heterogeneity in local
graph structures and node attributes. This inherent diversity among subgraphs leads to substantial
difficulties when attempting to aggregate local GNN models into a unified global model, as traditional
FL algorithms [20, 14] typically assume homogeneous data distributions across clients.
To tackle the non-IID challenges inherent in subgraph federated learning, personalized FL [ 29] has
recently emerged as a promising paradigm, which aims to provide client-specific GNN models rather
than enforcing a universal global solution. Existing personalized subgraph FL approaches commonly
achieve personalization by clustering clients on the server side, necessitating a reliable measure of
client similarity without direct access to client-side data. In this work, we impose even stricter privacy
constraints: neither raw data nor embeddings are shared, and only model learnable parameters can be
exchanged. Although the server could compare clients by directly measuring similarity between their
39th Conference on Neural Information Processing Systems (NeurIPS 2025).

## Page 2

Server -side Federated Aggregation
sLocal Learning in Subgraph Clients
APV Global 
GNN 
Client 1
Client 2
Client KServerAuxiliary 
Projections
Update Global Parameters
Client Similarity 
Matrix
Figure 1: The overall framework of FedAux . Left: The server maintains a global GNN model
together with learnable auxiliary projection vectors ( APVs) that are broadcast to all clients at the
start of each communication round. Middle: Clients jointly optimize the GNN and APVduring local
training, where the APVprojects node embeddings onto a 1D ak-space that positions related nodes
closer together. Right: After local training, clients transmit their optimized GNN parameters and
personalized APVs to the server. The server computes a client similarity matrix by comparing the
learned APVs, which captures the heterogeneity across subgraphs without accessing raw data. These
similarities determine personalized aggregation weights. At the end of each round, the updated global
parameters are broadcast for the next communication round.
parameter matrices uploaded, the high dimensionality of these matrices makes such metrics unreliable
under the curse of dimensionality [ 4]. Recent improvements have proposed measuring similarity by
comparing communication -level parameter gradients [ 35] or generating a common anchor graph on
the server as a neutral testbed [ 3]. Although these strategies mitigate some limitations, they remain
largely heuristic and do not explicitly model the heterogeneity inherent in subgraph clients (See
extended discussion in Appendix A).
MotivationOur key insight is that a compact, low-dimensional proxy, derived directly from the
client’s own model parameters, can faithfully summarize local subgraph characteristics without
leaking sensitive node features or embeddings. Such a proxy remains compact enough to avoid
the pitfalls of high-dimensional similarity measures, yet expressive enough to reflect meaningful
differences between clients. By learning this proxy jointly with the GNN parameters in each client,
and using it to guide both local adaptation and server-side aggregation, we obtain a principled,
privacy-preserving mechanism for personalization that directly leverages model parameters as a
stand-in for subgraph information.
ContributionIn this work, we propose FedAux , which employs differentiable auxiliary projections
to effectively capture and exploit client-specific heterogeneity for subgraph FL. As illustrated on
the left of Fig. 1, the server stores not only a global GNN but also a learnable auxiliary projection
vector ( APV) that accompanies the model parameters. At the start of the first communication round,
the server broadcasts the global GNN and the current APVto all clients. Each client projects its
node embeddings onto the APV, which is treated as a one-dimensional latent space. A differentiable
soft-sorting operator then orders the projected embeddings by similarity, after which a simulated
1D convolution aggregates the sorted embedding sequence. The aggregated representations drive a
supervised loss that simultaneously refines the local GNN and the APV, so that the optimized APV
preserves the relational structure of the client subgraph. Upon completing local training, clients send
their updated GNN weights and personalized APVs back to the server. Since the APVreveals only
the latent space that best preserves local node relationships while concealing the exact position of
every node in this space, it acts as a compact privacy-preserving summary of the client subgraph.
Then the server computes similarity among the returned APVs to quantify inter-client affinity and
yields client-specific aggregation weights. The server uses these weights to combine the incoming
parameters, producing a personalized model for each client that respects both shared knowledge and
local subgraph idiosyncrasies.
2

## Page 3

Furthermore, we establish comprehensive and rigorous theoretical analyses that justify the soundness
and interoperability of every technique used in FedAux . Extensive federated node classification
experiments on six datasets, spanning diverse graph domains and client scales, demonstrate that
FedAux achieves better accuracy and stronger personalization than state-of-the-art personalized
subgraph FL baselines.
2 Problem Statement: Subgraph Federated Learning
In Federated Learning (FL), multiple clients collaboratively train a global model without exchanging
their raw data. In thesubgraph federated learningsetting, each client holds a subgraph of a larger
graph. Formally, let a graph Gbe partitioned (or subsampled) into Ksubgraphs {G1, G2,···, G K}
asKclients, where Gk= (V k, Ek, Xk, Yk). Here, Vk={v k,1,···, v k,Nk}is the set of nodes in the
k-th subgraph with Nk=|V k|nodes, Ekthe set of edges among those nodes, Xk∈RNk×dthe node
features, and Ykthe labels relevant to the learning task. In our FL scenario, each client Gihas access
only to its local data (i.e., its subgraph structure, node features, and labels), and there is no sharing of
raw data or any node embeddings between clients.
A typical GNN fθk(Gk)parameterized by θkis employed to produce node embeddings and ultimately
generate predictions on the client Gk. In a standard federated learning setting such as FedAvg [ 20],
one aims to solve the global objective: minθPK
k=1αkLk(θ), subject to the privacy constraint
that raw local data Gknever leaves the client side. A common choice is to weight client Gkby
αk=N k/ PK
j=1Nj
or simply αk= 1/K . The iterative procedure proceeds as follows. First,
the server initializes θ(0). At each global communication round t∈ {1,···, T} , it sends θ(t−1)to
each client. Gkthen updates θ(t−1)locally by taking a few stochastic gradient steps on Lk(θ)to
update the parameters θk←θk−η∇L , which produce Gk’s optimal local parameters θ(t)
k. After the
t-th local training, all clients’ locally updated parameters {θ(t)
1,···θ(t)
K}are sent back to the server,
which aggregates them via a weighted average θ(t)=PK
k=1αkθ(t)
k. The newly aggregated global
parameters θ(t)are then broadcast back to each client for the next communication round. When the
process converges or reaches a designated number of rounds, the final global parameters θ(T)are
taken as the parameters of the GNN model on the server.
3 Methodology
In this section, we introduce the proposed Subgraph Federated Learning with Auxiliary Projections
(FedAux ) framework, designed to address the heterogeneity across local subgraphs in federated
learning. Fig. 1 illustrates an overview of FedAux . Our objective is twofold: 1) Each client locally
encodes its subgraph into a one-dimensional space via a learnable auxiliary projection vector APV,
and 2) the server then exploits these auxiliary vectors to realize personalized aggregation.
3.1 Client-Side Local Training
Before the first communication round t= 0 , alongside the GNN model parameterized by θ(0),
the server also maintains a learnable APVa(0)∈Rd′. During each communication round t, the
server distributes (θ(t−1),a(t−1))to initialize all clients’ local model {(θ(t−1)
k,a(t−1)
k)}K
k=1← 
θ(t−1),a(t−1)
. For a clientG k, it runs the local GNN model to optimize the node embeddings:
H(t−1)
k=fθ(t−1)
k(Gk) =h
h(t−1)
k,1, h(t−1)
k,2,···, h(t−1)
k,Nki
∈RNk×d′,(1)
where d′is the output dimension of node embeddings. Given the local APVa(t−1)
k , we first
normalize all node embeddings so that all embeddings are compared on a consistent scale as
ˆh(t−1)
k,i=h(t−1)
k,i/max j∥h(t−1)
k,j∥. Then the similarity between node vk,ianda(t−1)
k is defined
ass(t−1)
k,i=⟨ˆh(t−1)
k,i,a(t−1)
k⟩, where ⟨·,·⟩ denotes the inner product in Rd′. Intuitively, s(t−1)
k,i can
be interpreted as the coordinate of each node vk,iinak-space, which is a 1D line. Since a(t−1)
k is
itself learnable, the client Gkis adaptively refining this space to capture relationships among its node
embeddings more effectively.
3

## Page 4

Next, Gkcollects the similarity scores S(t−1)
k={s(t−1)
k,1,···, s(t−1)
k,Nk}and sort them in non-
decreasing order. Letπ kbe the permutation that orders these scores:
s(t−1)
k,πk(1)≤s(t−1)
k,πk(2)≤ ··· ≤s(t−1)
k,πk(Nk),(2)
where πk(j)represents the node index at rank j. Accordingly, we apply this permutation πkto the
row indices ofH(t−1)
k, which yields the sorted embedding matrixa(t−1)
kas:
eH(t−1)
k=h
H(t−1)
ki
πk,:=h
h(t−1)
k,πk(1), h(t−1)
k,πk(2),···, h(t−1)
k,πk(Nk)i
,(3)
2
51
4 253
1
3
42
1
3
4
5
Local Training
Figure 2: The local training of FedAux aims
to map all nodes in Gkto a corresponding
ak-space, and the optimization objective is
to learn the APVa k, such that the resulting
ak-space preserves the optimal node sorting.which aligns node embeddings according to their
coordinates in the ak-space. As shown in Fig. 2,
during local training, the node embeddings and the
structure of the ak-space are jointly optimized so
that nodes with stronger relationships are positioned
closer along this learned space (in Gkcomprising
two triangles, nodes within the same triangle should
be proximate in the ak-space). In other words, the
objective of the local model is to adaptively reshape
theAPVso that the induced node sorting effectively
captures the local data information.
Under the semi-supervised setting, the node sorting
onAPVcan be adaptively refined under the guidance
of the downstream task. Thinking of each h(t−1)
k,πk(i)as
a feature vector in a 1D sequence eH(t−1)
k , inspired by [ 18], we can apply a 1D convolution with a
fixed kernel size BovereH(t−1)
kasConv1D(h
h(t−1)
k,πk(1), h(t−1)
k,πk(2),···, h(t−1)
k,πk(Nk)i
). More specifically,
for each nodev πk(i)in the sorted sequence, the convolution can be written as:
z(t−1)
k,πk(i)=⌊B/2⌋X
τ=−⌊B/2⌋Wτh(t−1)
k,πk(i+τ)+b,(4)
where Wτ∈Rd′×d′are learnable convolution kernels for offset τ, and bis a bias term. Convolving
around vπk(i)in Eq. (4) amounts to a proximity-based aggregation in the ak-space, where each
embedding is updated by aggregating information from its neighbors along this learned 1D sorting.
Hence, the quality of this sorting significantly impacts the aggregation effectiveness. Intuitively,
nodes with stronger semantic relationships or similar labels should appear closer together in this
learned sorting. We can formulate the learning objective to explicitly optimize the sorting induced
by the APVa k, ensuring that the resultant sorting facilitates effective aggregation and improves
downstream predictive accuracy. Consequently, we formulate the learning objective:
(θ∗
k,a∗
k,Φ∗
k) = argmin
θk,ak,ΦkL
CLF
Conv1D
˜H(t−1)
k
, Yk
,(5)
where Φkdenotes the full set of parameters for Conv1D and the subsequent classifier CLF that maps
node embeddings to final logits. Through this objective, we explicitly encourage ak-space to yield
an optimal node sorting, enabling the convolutional operation to effectively capture and leverage
localized, label-informed relationships, thereby the optimized APVa(t)
k=a∗
kaccurately preserves
and encodes the local node relationships specific to each client.
However, akdoes not directly participate in the loss defined in Eq. (5) in a way that enables standard
backpropagation to update it. It is because the role of akis limited to generating similarity scores,
which in turn determine the input order to the Conv1D layer. Thus, akonly affects the network’s
output by reordering embeddings, which is a purely indirect pathway that does not produce a gradient
signal for akfrom the downstream loss. [ 18] attempted to mitigate this by multiplying each node
embedding by its similarity score and then sorting. While this modification integrates akinto the
learning pipeline directly, the hard discrete sort persists, causing the gradient signal that could refine
akto be still routed through a non-smooth transformation. Hence akstill cannot be fully optimized
to reorder embeddings based on loss feedback, leaving the core issue unresolved.
4

## Page 5

To eliminate the hard-sorting bottleneck, we propose acontinuous aggregationscheme over the
ak-space. Rather than ranking or discretizing these similarity scores, for each node vi, we
define a continuous kernel κ(s(t−1)
k,i, s(t−1)
k,j), which could be a simple Gaussian-like function
Kij=κ(s(t−1)
k,i, s(t−1)
k,j) = exp
−(s(t−1)
k,i−s(t−1)
k,j)2/σ2
with bandwidth σ >0 , measuring
how close vjis toviin the real line spanned by {s(t−1)
k}. As shown in the right part of Fig. 1, we then
obtain an aggregated embedding for each node viby a smooth weighted sum of all node embeddings:
z(t−1)
k,i=1
MiNkX
j=1κ
s(t−1)
k,i, s(t−1)
k,j
h(t−1)
k,j, M i=NkX
j=1κ
s(t−1)
k,i, s(t−1)
k,j
.(6)
Unlike discrete sorting, this continuous aggregator is fully differentiable with respect to ak, because
changes in aksmoothly shift each s(t−1)
k,i and thus adjust the kernel weights κ. This approach
naturally learns to group nodes with similar s(t−1)
kvalues, emulating the sorted 1D convolution effect,
while sidestepping the gradient-blocking issues that arise from hard-sorting steps.
To jointly train the GNN parameters θkand the APVa k, we associate each node viwith two
embeddings: h(t−1)
k,i produced by the GNN defined in Eq. (1), and z(t−1)
k,i generated via our kernel-
based aggregation method as Eq. (6). We then concatenate these embeddings to form vi’s final
embedding r(t−1)
k,i= [h(t−1)
k,i∥z(t−1)
k,i], which is fed into a simple MLP classifier CLF(·) to produce
logits for the cross-entropy lossL k=1
NkCE(CLF(Γ(t−1)
k), Yk), whereΓ(t−1)= [r(t−1)
k,i]Nk
i=1.
3.2 Server-Side Federated Aggregation
At the end of local training for communication round t, each client Gktransmits its optimized
parameters (θ(t−1)
k,a(t−1)
k)to the server. In doing so, only these high-level parameters are exchanged,
rather than gradients or node embeddings, thereby limiting direct leakage of private subgraph
information. Note that akserves as the optimal subspace for capturing node relationships, how
individual nodes map into this space (and thus the precise relational details) remains unknown
to the server. This design strictly adheres to the fundamental FL principle thatData stays local; only
model updates leave.
Since the data distributions across clients can be non-IID, the server is expected to personalize the
aggregation for each client. Given that each a(t−1)
kcan be a descriptor of how node embeddings in
Gkare arranged and structured, the similarity between two clients GkandGlcan be measured via
the cosine similarity of their APVs:SIM(a(t−1)
k,a(t−1)
l) =D
a(t−1)
k,a(t−1)
lE
a(t−1)
ka(t−1)
l. We then convert this
similarity into a weight:
w(t−1)
k,l=exp
αSIM
a(t−1)
k,a(t−1)
l
PK
r=1exp
αSIM
a(t−1)
k,a(t−1)
r,(7)
where α >0 is a temperature controlling the sharpness of the weighting distribution. w(t−1)
k,lreflects
how much client Gkshould incorporate the update from Gl. By emphasizing contributions from
similar clients (i.e., those with high similarity in their APVs), each client’s final model can better
handle heterogeneous data while reducing interference from dissimilar clients. Instead of averaging
all local parameters into one single global model, the server can compute a personalized aggregation
of parameters for each clientG kas:
θ(t)
k=KX
l=1w(t−1)
k,lθ(t−1)
l,a(t)
k=KX
l=1w(t−1)
k,la(t−1)
l.(8)
Thus, after the server performs these personalized aggregations for both θanda, it transmits
(θ(t)
k,a(t)
k)back to client Gkfor the (t+ 1) -th communication round starting point. Appendix B
shows the pseudo code ofFedAux.
5

## Page 6

Complexity AnalysisFor the client side of FedAux , the local GNN embedding generation incurs
a complexity of O(|E k|d′), and the auxiliary projection from embeddings to the APV results in
O(N kd′). Besides, the kernel-based embedding aggregation over the 1D space induced by the APV
has complexity O(N2
kd′). Consequently, the per-client complexity is O(|E k|d′+N2
kd′). On the
server side, computing the client-wise similarity for personalized federated aggregation involves
a complexity O(K2d′). Therefore, the total complexity of FedAux per communication round is
O 
(|Ek|+N2
k+K2)d′
.
3.3 Theoretical Analysis
For notational simplicity, we focus on a single client with Nnodes in a given communication round
and omit the subscript kand superscript (t−1) . The core of our model is to use a learnable auxiliary
projection vector APVa to capture an optimal node sorting of the local node embeddings and thus
serves as a compact summary of the subgraph. However, there is a foundational question that
inevitably arises once we replace hard sorting with the smooth kernel aggregator: when the APVa
is learned via back -propagation,what does it actually learn? Does it encode an arbitrary nuisance
direction, or does it converge to a geometrically meaningful axis that faithfully summarizes the local
subgraph?To answer these questions, we analyze the fidelity of the APVwith the following theorem.
Theorem 3.1(Fidelity of the APVa ).Let C:=1
NPN
i=1hih⊤
ibe the empirical covariance of node
embeddings in the current client with size N. The gradient of the local loss Lw.r.t. the APVa
satisfies:
∇aL=−2
σ2Ca+R(σ),(9)
where the remainder term obeys ∥R(σ)∥=O(σ0)asσ→0+. Define Sd−1={x∈Rd:∥x∥ 2= 1}
as the unit Euclidean sphere embedded in Rd, then the gradient descent on Lwith unit-norm re-
normalization reproduces Oja learning rule [22]:
a←Π Sd−1(a−ηCa),(10)
whose unique stable fixed points are the eigenvectors of C, and the global attractor is the principal
eigenvector (largest eigenvalue).
The proof and more discussions are provided in Appendix C.1. It guarantees that, once the kernel
aggregator makes adifferentiable, ordinary back-propagation forces APVto align with the direction
along with the node embeddings in that client vary the most. Equivalently, the APVa is not an arbitrary
trainable knob but a statistically optimal, variance -maximizing summary of local embeddings. Thus,
theAPVais provably the first principal component of the local embeddings.
In Section 3.1, we propose a continuous kernel aggregator to replace the hard sort-then- Conv1D
pipeline used in earlier work [ 18]. To justify that replacement, the following theorem rigorously
shows that the new smooth operator degenerates to the old one in the appropriate limit.
Theorem 3.2(Sorting limit and equivalence to Conv1D ).Let zibe the kernel-smoothed embeddings,
and gather them in score order eZ=
zπ(1),···, z π(N)
∈RN×d′. The original sorted embeddings
eH= [h π(1),···, h π(N)]is defined in Eq.(3). Let W∈RB×d′be an arbitrary fixed Conv1D
kernel with zero padding, and denote ConvW(X)t=PB
τ=1WτXt+τ−⌈B/2⌉ , for any sequence
X ∈RN×d′. Then we have:
lim
σ→0+ConvW
eZ
−ConvW
eH
F= 0,(11)
where∥ · ∥ Fis the Frobenius norm.
The proof is in Appendix C.2. Theorem 3.2 indicates that the kernel aggregation followed by
Conv1D converges to hard-sorting followed by Conv1D as the bandwidth σtends to 0. Hence, the
two architectures have identical expressive power up to an arbitrarily small error for sufficiently small
σ. Although the limit σ→0+recovers discrete sorting, a larger σperforms a soft neighborhood
pooling that can act as a learnable regularizer against over -fitting noisy local orderings. In practice,
we findσ= 1to be effective across all datasets.
Next, we present a theoretical analysis of FedAux ’s convergence rate, which guarantees that it cannot
diverge in expectation. Since this analysis focuses on the global model, we use the subscript ·kto
denote the client index.
6

## Page 7

Table 1: Federated node classification results. The reported results are the mean and standard
deviation over three different runs. Best performance is highlighted inbold.
Cora CiteSeer Pubmed
Methods 5 Clients 10 Clients 20 Clients 5 Clients 10 Clients 20 Clients 5 Clients 10 Clients 20 Clients
Local 81.30±0.2179.94±0.2480.30±0.25 69.02±0.0567.82±0.1365.98±0.17 84.04±0.1882.81±0.3982.65±0.03
FedAvg 74.45±5.6469.19±0.6769.50±3.58 71.06±0.6063.61±3.5964.68±1.83 79.40±0.1182.71±0.2980.97±0.26
FedProx 72.03±4.5660.18±7.0448.22±6.81 71.73±1.1163.33±3.2564.85±1.35 79.45±0.2582.55±0.2480.50±0.25
FedPer 81.68±0.4079.35±0.0478.01±0.32 70.41±0.3270.53±0.2866.64±0.27 85.80±0.2184.20±0.2884.72±0.31
GCFL 81.47±0.6578.66±0.2779.21±0.70 70.34±0.5769.01±0.1266.33±0.05 85.14±0.3384.18±0.1983.94±0.36
FedGNN 81.51±0.6870.12±0.9970.10±3.52 69.06±0.9255.52±3.1752.23±6.00 79.52±0.2383.25±0.4581.61±0.59
FedGTA 71.26±2.9368.33±1.2769.24±0.91 69.39±0.7567.34±1.0865.29±1.92 78.47±0.2582.79±0.2081.92±0.60
FedSage+ 72.97±5.9469.05±1.5957.97±12.6 70.74±0.6965.63±3.1065.46±0.74 79.57±0.2482.62±0.3180.82±0.25
FED-PUB 83.72±0.1881.45±0.1281.10±0.64 72.40±0.2671.83±0.6166.89±0.14 86.81±0.1286.09±0.1784.66±0.54
FedAux84.57±0.3982.05±0.7181.60±0.64 72.99±0.8273.16±0.2968.10±0.35 88.10±0.1686.43±0.2084.87±0.42
Amazon-Computer Amazon-Photo ogbn-arxiv
Methods 5 Clients 10 Clients 20 Clients 5 Clients 10 Clients 20 Clients 5 Clients 10 Clients 20 Clients
Local 89.22±0.1388.91±0.1789.52±0.20 91.67±0.0991.80±0.0290.47±0.15 66.76±0.0764.92±0.0965.06±0.05
FedAvg 84.88±1.9679.54±0.2374.79±0.24 89.89±0.8383.15±3.7181.35±1.04 65.54±0.0764.44±0.1063.24±0.13
FedProx 85.25±1.2783.81±1.0973.05±1.30 90.38±0.4880.92±4.6482.32±0.29 65.21±0.2064.37±0.1863.03±0.04
FedPer 89.67±0.3489.73±0.0487.86±0.43 91.44±0.3791.76±0.2390.59±0.06 66.87±0.0564.99±0.1864.66±0.11
GCFL 89.07±0.9190.03±0.1689.08±0.25 91.99±0.2992.06±0.2590.79±0.17 66.80±0.1265.09±0.0865.08±0.04
FedGNN 88.08±0.1588.18±0.4183.16±0.13 90.25±0.7087.12±2.0181.00±4.48 65.47±0.2264.21±0.3263.80±0.05
FedGTA 85.06±0.8284.27±0.7179.46±0.28 89.70±0.6776.53±3.2182.02±0.78 65.42±0.0964.22±0.0863.75±0.18
FedSage+ 85.04±0.6180.50±1.3070.42±0.85 90.77±0.4476.81±8.2480.58±1.15 65.69±0.0964.52±0.1463.31±0.20
FED-PUB 90.25±0.0789.73±0.1688.20±0.18 93.20±0.1592.46±0.1990.59±0.35 67.62±0.1166.35±0.1663.90±0.27
FedAux90.38±0.0889.92±0.1588.35±0.96 93.37±0.2692.30±0.2990.91±0.60 68.83±0.1568.50±0.2765.52±0.10
Theorem 3.3(Global linear convergence).Let Ψ(t)
k= (θ(t)
k,a(t)
k)be the local parameters of client Gk
at the communication round t, and Ψ(t)=h
Ψ(t)
1,···,Ψ(t)
ki
collects all local parameters. Assuming
1) every local objective is L-smooth: ∀Ψk,Ψ′
k:∥∇L k(Ψk)− ∇L k(Ψ′
k)∥ ≤L∥Ψ k−Ψ′
k∥; 2)
the stochastic gradients are unbiased ( E[gk] =∇L k) and variance-bounded ( Eh
∥gk− ∇L k∥2i
≤
ζ2), where gk:=∇ (Ψk)Lkmeans the local gradients; 3) each local objective satisfies the µ-PL
condition [ 23]; 4) let Ω(t)= [w(t)
kl]k,l∈RK×K, the spectral gap ρ:= suptΩ(t)−1
K11⊤
2<1.
Let each client perform Qlocal updates per round, and the learning rate 0< η≤1
2L. With any
initial parametersΨ(0)= (θ(0),a(0)), we have:
Eh
L
Ψ(T)
− L⋆i
≤(1−ηµ)QT
L
Ψ(0)
− L⋆
+ηLζ2
2µ+2ηLρ2
µ(1−ρ)2,(12)
whereL(Ψ) :=PK
k=1pkLk(Ψk)is the global objective with client sampling probability pk(w.l.o.g.,
pk= 1/K).L⋆:=P
kpkL⋆
kis the weighted optimal value.
The proof is in Appendix C.3. In Theorem 3.3, the first term decays linearly; the second is the
classical SGD variance term; the third is the personalization error and vanishes as ρ→0 . Thus
FedAuxcan linearly descend to a neighborhood of the global optimum.
4 Experiments
4.1 Experimental Setup
Datasets and Experimental SettingsFollowing previous works [ 40,3,42], we construct dis-
tributed subgraphs from benchmark datasets by partitioning each original graph into multiple sub-
graphs corresponding to individual clients. Specifically, we perform experiments on six widely used
datasets, including four citation networks (Cora, CiteSeer, Pubmed [ 25], and ogbn-arxiv [ 10]) and
two product co-purchase networks (Amazon-Computer and Amazon-Photo [ 19,26]). We employ
METIS [ 12] as our default graph partitioning algorithm, which allows explicit specification of the
desired number of subgraphs without overlapping. Based on these datasets, we follow the standard
experimental setup used in personalized subgraph federated learning literature [ 3,42]. Specifically,
7

## Page 8

024681012141618
Clients0
2
4
6
8
10
12
14
16
18Clients
0.20.40.60.81.0
(a) Embedding Similarity
024681012141618
Clients0
2
4
6
8
10
12
14
16
18Clients
0.20.40.60.8
 (b)APV-based Similarity
024681012141618
Clients0
2
4
6
8
10
12
14
16
18Clients
0.40.60.81.0
 (c) Weight Similarity
024681012141618
Clients0
2
4
6
8
10
12
14
16
18Clients
0.00.20.40.60.81.0
 (d) Functional Similarity
Figure 3: Client similarity based on different measures. Darker colors indicate higher similarity.
for dataset splitting, we randomly sample 20%/40%/40% of nodes from each subgraph for training,
validation, and testing, respectively. The only exception is the ogbn-arxiv dataset, due to its signif-
icantly larger size. For this dataset, we randomly select 5% of the nodes for training, half of the
remaining nodes for validation, and the rest for testing. Dataset statistics and implementation details
can be found in Appendix D.
Baselines FedAux is compared against several representative federated learning (FL) methods,
including general FL baselines: FedAvg [ 20], FedProx [ 14], and FedPer [ 2]; as well as specialized
graph-based FL models1: GCFL [ 35], FedGNN [ 34], FedGTA [ 16], FedSage+[ 40], and FED-PUB[ 3].
Additionally, we consider a local variant of our model (Local), where FedAux is trained independently
at each client without parameter sharing.
4.2 Main Results
Table 2: Degree of non-IIDness. Pubmed ex-
hibits the lowest non-IIDness, and Amazon-
Photo has the highest.
Pubmed
Non-IIDness 5 Clients 10 Clients 20 Clients
ξ0.1316 0.1500 0.1725
Amazon-Photo
Non-IIDness 5 Clients 10 Clients 20 Clients
ξ0.3398 0.3668 0.4307As summarized in Table 1, FedAux is the only algo-
rithm that wins every dataset–client-count combi-
nation, indicating that the APV-driven personaliza-
tion generalizes from small citation graphs (Cora,
CiteSeer) to large-scale, high-dimensional graphs
(ogbn-arxiv). Specifically, relative to the strongest
competitor in each column, FedAux achieves ac-
curacy improvements ranging from 0.2% to 2.4%.
The margin over the canonical FedAvg is more
pronounced, with an average gain of 4.5%, un-
derscoring that the proposed auxiliary projection
mechanism confers benefits well beyond classical
weighted averaging. Further, to quantify statistical heterogeneity (i.e., degree of non-IIDness), we
adopt ξ=JSD+MMD where the Jensen–Shannon Divergence (JSD) captures label-distribution
skew and the Maximum Mean Discrepancy (MMD) captures disparities in subgraph structure (formal
definition in Appendix D.3). Higher values of ξindicate stronger non-IIDness. As reported in Table 5
of Appendix D.3, ξrises monotonically for every dataset as the federation enlarges from 5 to 20
clients, confirming that our partition protocol indeed induces progressively harsher heterogeneity.
This trend is mirrored in the performance of all methods, whose accuracies decline with larger client
counts. Nevertheless, the drop for FedAux is consistently the smallest: on Cora, accuracy falls by
only 2.9%, while FedAvg and FedProx lose nearly 7%. To highlight the contrast, we single out the
most IID dataset Pubmed and the most non-IID dataset Amazon-Photo in Table 2. The results under
these settings show that FedAux remains the top performer in both extremes, indicating that our
model is merely tuned for gentle partitions but retains its edge under pronounced non-IID conditions.
4.3 Model Analysis
Effectiveness of APV-based Client Similarity EstimationTo intuitively show that the auxiliary
projection vector APVcan accurately capture the latent similarity among clients under non-IIDness, we
construct a synthetic graph (See Appendix D.4) that jointly embodies the two types of heterogeneity:
1We exclude weakly privacy-protected baselines such as FedGCN [ 37], GraphFL [ 32], and FedStar [ 30] as
these methods leak node embeddings, connectivities, or local gradients.
8

## Page 9

Table 3: Attack AUC of MIA.
Dataset FedGNN FedGTA FedAux
Cora0.56 0.540.51
Pubmed0.58 0.550.52
ogbn-arxiv0.55 0.530.49
FED-PUB FedGTA FedSage+65.067.570.072.575.077.580.082.585.0Accuracy (%)81.45
68.3369.0582.02
70.1271.00Original
With APV
(a) Cora
FED-PUB FedGTA FedSage+808182838485868788Accuracy (%)86.09
82.7982.6286.45
84.01 84.10Original
With APV (b) Pubmed
FED-PUB FedGTA FedSage+7880828486889092Accuracy (%)89.73
84.27
80.5091.02
86.15
81.93Original
With APV (c) Amazon-Computer
Figure 4: Transferability ofAPV.
0.05 0.10 0.15 0.20
Average clustering time (s)510152025303540Peak memory during clustering (MB)FedAux
FED-PUB
GCFL
(a)Cora with 10 clients
6 8 10 12 14
Average clustering time (s)50100150200Peak memory during clustering (MB)FedAux
FED-PUB
GCFL (b)ogbn-arxiv with 10 clients
Figure 5: Server-side clustering cost.
1 10 20 30 40 50 60 70 80 90 100
Communication Rounds304050607080Local Accuracy (%)
FedAux FedAvg(a)Cora with 10 clients
1 10 20 30 40 50 60 70 80 90 100
Communication Rounds304050607080Local Accuracy (%)
FedAux FedAvg (b)Cora with 20 clients
Figure 6: Averaged local accuracy concerning
communication rounds.
label heterogeneity and subgraph (structural and feature) heterogeneity. Results in Fig. 3 demonstrate
that the APV-based client similarity can best recover the ground -truth client relationships. Each APV
converges to the principal axis of its client’s embedding distribution, yielding highly aligned directions
within the same group and near -orthogonal directions across different groups (Theorem 3.1). Thus
APVcan serve as a privacy-preserving yet information-rich descriptor in subgraph FL.
Membership Inference Attacks (MIA)We add a comprehensive empirical privacy evaluation via
MIAs to rigorously test whether our APV-based framework leaks sensitive information. We assume
an honest -but-curious server with full access to the entire history of a client’s APVa kand its GNN
parameters θk. The goal of the server is to decide whether a probe embedding hproboriginated
from client Gk, using only (ak, θk), while raw data, node embeddings, and gradients are never
shared. Following the standard MIA methodology [ 21,27], the server trains an attack classifier
gk(ak, θk, hprob)implemented as a two -layer MLP with hidden size 64, to output the probability
thathprobbelongs to the training set of Gk. The attack is trained by maximum likelihood on a
held-out mixture of member against non -member probes. In Table 3, we compare FedAux against
representative subgraph FL baselines on three datasets using identical client partitions to those in
our main experiments, and report the Attack AUC (lower values indicate better privacy) averaged
over five random seeds. The results show that MIAs against FedAux achieve AUCs in the range
[0.49,0.52] , which is indistinguishable from random guessing. This demonstrates that APVs do not
leak sensitive membership information and actually provide stronger privacy than baselines.
Transferability of APV To examine whether APVcan generalize beyond FedAux and serve as a
plug-and-play personalization module, we integrate it into representative subgraph FL baselines.
Specifically, we replace FED-PUB’s functional embedding similarity with APV, and jointly train
APVwith FedGTA and FedSage+. All variants are trained under the same 10-client non-IID split
on three datasets. Fig. 4 shows that APVconsistently improves each baseline across datasets. For
example, FedGTA with APVachieves 1%-2% higher accuracy than its original counterpart. These
improvements confirm that APVfunctions as a generic, lightweight, and privacy-preserving similarity
proxy that can be seamlessly integrated with diverse subgraph FL frameworks.
Clustering Efficiency on ServerTo perform personalized FL, FED-PUB uses soft clustering by
running a proxy graph through each client model and comparing embeddings. GCFL applies hard
clustering, grouping clients with a Stoer-Wagner cut on cross-round gradients. Our APV-based method
only computes similarity between the uploaded vectors, requiring no extra forward passes, gradient
logging or cut computation, so server overhead is minimal. As Fig. 5 illustrates, the APVmethod
attains the fastest clustering time and the lowest peak memory, making it more efficient at scale.
9

## Page 10

Convergence RatesFig. 6 compares the convergence behavior of FedAux and FedAvg. Notably,
FedAux converges by the 60th communication round in both the 10 -client and 20 -client settings.
Since the latter involves a higher level of data heterogeneity, it indicates that FedAux maintains a
consistent convergence speed even as the degree of non-IIDness increases.
In Appendix E, we conduct an ablation study to investigate the impact of our proposed continuous
aggregation scheme, which encodes local node relationships in the 1D space induced by the APV, as
well as the effect of the server-side APV-based personalized federated aggregation. We also conduct
experiments to analyze the sensitivity to hyperparameters.
5 Related Work
For generalFederated Learning, FedAvg [ 20] first demonstrated that deep models can be trained
on decentralized data with iterative model averaging. Subsequent work revealed that statistical and
systems heterogeneity slow or destabilize FedAvg’s convergence, which has been formally addressed
by proximal correction [ 14], variance reduction [ 11], and data–distribution smoothing through a small
globally shared subset of samples [ 43]. Optimization refinements such as normalized aggregation [ 33],
adaptive server updates [ 24] and dynamic regularization [ 1] further tighten convergence guarantees
under extreme non-IID settings. Beyond a single global model, personalization frameworks, e.g.,
Ditto [ 15], which jointly optimizes a shared model and client-specific objectives, explicitly trade off
fairness, robustness, and local adaptation. These advances establish the algorithmic and theoretical
foundations on which federated graph learning is built.
ForGraph Federated Learning[ 36,17,39,38], at the node level, FedGCN [ 37] illustrates that
one-shot encrypted exchange can suffice to federate GCNs while maintaining accuracy and privacy;
GCFL [ 35] clusters clients by gradient dynamics to mitigate structural and feature shift across
graphs. To combat cross-domain heterogeneity, FedStar [ 30] extracts a domain-invariant topology
that generalizes across diverse graphs, and FedGraph [ 9] augments local data by requesting node
information from other clients. When each participant owns only a fragment of a larger network,
subgraph federated learning methods such as FedSage/FedSage+ [ 40] generate virtual neighbours
to repair missing cross-subgraph edges. FED-PUB [ 3] proposes to generate functional embeddings
to evaluate the similarity between clients for personalized aggregation. These models collectively
highlight an open challenge for personalized graph FL, i.e., accurate client similarity measures, which
our proposedFedAuxaddresses through end-to-end learning of auxiliary projection vectors.
Several new methods further extend personalization but come with non-trivial trade-offs. FedSSP [ 31]
transmits spectral components that are invariant across domains but can leak sensitive local spectral
information. FedEgo [ 41] shares ego-network embeddings, which directly expose structural patterns.
PFGNAS [ 8] leverages prompt-based neural architecture search without server-side similarity esti-
mation, but its reliance on LLM-based personalization introduces prohibitive cost. FedGrAINS [ 5]
personalizes within each client by learning with a GFlowNet, thereby avoiding server-side mixing,
but at the expense of training an additional model with high compute and memory overhead. While
the aforementioned methods contribute interesting ideas, they either compromise privacy guarantees
(e.g., FedSSP, FedEgo) or impose heavy computational costs (e.g., PFGNAS, FedGrAINS), limiting
their practicality. In contrast, our method learns Auxiliary Projection Vectors ( APV) in an end-to-end
manner: lightweight, privacy-preserving client signatures that avoid raw data or embedding leakage,
yet enable effective similarity-aware aggregation for personalized subgraph FL.
6 Conclusion
We present FedAux , a personalized subgraph federated learning framework that augments each
local GNN with learnable auxiliary projection vectors ( APVs). Specifically, besides the global GNN
parameters, the server initializes and distributes APVs to each client, enabling effective and privacy-
preserving characterization of local subgraph structures. By continuously projecting node embeddings
onto a 1D space induced by these APVs, local models adaptively refine the APVs to optimally capture
node relationships within each client’s subgraph. After each communication round, the server
leverages similarity between client APVs to perform personalized model aggregation. Extensive
experiments across multiple datasets with varying numbers of clients validate the effectiveness of
APVs as informative descriptors for personalized subgraph FL.
10

## Page 11

Acknowledgements
The research is supported, in part, by the Ministry of Education, Singapore, under its Academic
Research Fund Tier 1 (RG101/24).
References
[1]Acar, D. A. E., Zhao, Y ., Matas, R., Mattina, M., Whatmough, P., and Saligrama, V . Fed-
erated learning based on dynamic regularization. InInternational Conference on Learning
Representations, 2021.
[2]Arivazhagan, M. G., Aggarwal, V ., Singh, A. K., and Choudhary, S. Federated learning with
personalization layers.arXiv preprint arXiv:1912.00818, 2019.
[3]Baek, J., Jeong, W., Jin, J., Yoon, J., and Hwang, S. J. Personalized subgraph federated learning.
InInternational conference on machine learning, pp. 1396–1415. PMLR, 2023.
[4] Bellman, R. Dynamic programming.science, 153(3731):34–37, 1966.
[5]Ceyani, E., Xie, H., Buyukates, B., Yang, C., and Avestimehr, S. Fedgrains: Personalized
subgraph federated learning with adaptive neighbor sampling. InProceedings of the 2025 SIAM
International Conference on Data Mining (SDM), pp. 598–607. SIAM, 2025.
[6]Csiszár, I. and Körner, J.Information theory: coding theorems for discrete memoryless systems.
Cambridge University Press, 2011.
[7]Delfour, M. C. and Zolésio, J.-P.Shapes and geometries: metrics, analysis, differential calculus,
and optimization. SIAM, 2011.
[8]Fang, H., Gao, Y ., Zhang, P., Yao, J., Chen, H., and Wang, H. Large language models enhanced
personalized graph neural architecture search in federated learning. InProceedings of the AAAI
Conference on Artificial Intelligence, volume 39, pp. 16514–16522, 2025.
[9]He, C., Balasubramanian, K., Ceyani, E., Yang, C., Xie, H., Sun, L., He, L., Yang, L., Yu, P. S.,
Rong, Y ., Zhao, P., Huang, J., Annavaram, M., and Avestimehr, S. Fedgraphnn: A federated
learning system and benchmark for graph neural networks, 2021.
[10] Hu, W., Fey, M., Zitnik, M., Dong, Y ., Ren, H., Liu, B., Catasta, M., and Leskovec, J. Open
graph benchmark: Datasets for machine learning on graphs.Advances in neural information
processing systems, 33:22118–22133, 2020.
[11] Karimireddy, S. P., Kale, S., Mohri, M., Reddi, S., Stich, S., and Suresh, A. T. Scaffold:
Stochastic controlled averaging for federated learning. InInternational conference on machine
learning, pp. 5132–5143. PMLR, 2020.
[12] Karypis, G. Metis: Unstructured graph partitioning and sparse matrix ordering system.Technical
report, 1997.
[13] Krasulina, T. The method of stochastic approximation for the determination of the least
eigenvalue of a symmetrical matrix.USSR Computational Mathematics and Mathematical
Physics, 9(6):189–195, 1969.
[14] Li, T., Sahu, A. K., Zaheer, M., Sanjabi, M., Talwalkar, A., and Smith, V . Federated optimization
in heterogeneous networks.Proceedings of Machine learning and systems, 2:429–450, 2020.
[15] Li, T., Hu, S., Beirami, A., and Smith, V . Ditto: Fair and robust federated learning through
personalization. InInternational conference on machine learning, pp. 6357–6368. PMLR,
2021.
[16] Li, X., Wu, Z., Zhang, W., Zhu, Y ., Li, R.-H., and Wang, G. Fedgta: Topology-aware averaging
for federated graph learning.Proc. VLDB Endow., pp. 41–50, 2023.
11

## Page 12

[17] Li, Z., Wang, X., Chen, H.-Y ., Shen, H. W., and Chao, W.-L. H. Fedne: Surrogate-assisted
federated neighbor embedding for dimensionality reduction.Advances in Neural Information
Processing Systems, 37:133948–133974, 2024.
[18] Liu, M., Wang, Z., and Ji, S. Non-local graph neural networks.IEEE transactions on pattern
analysis and machine intelligence, 44(12):10270–10276, 2021.
[19] McAuley, J., Targett, C., Shi, Q., and Van Den Hengel, A. Image-based recommendations on
styles and substitutes. InProceedings of the 38th international ACM SIGIR conference on
research and development in information retrieval, pp. 43–52, 2015.
[20] McMahan, B., Moore, E., Ramage, D., Hampson, S., and y Arcas, B. A. Communication-
efficient learning of deep networks from decentralized data. InArtificial intelligence and
statistics, pp. 1273–1282. PMLR, 2017.
[21] Nasr, M., Shokri, R., and Houmansadr, A. Comprehensive privacy analysis of deep learning:
Passive and active white-box inference attacks against centralized and federated learning. In
2019 IEEE symposium on security and privacy (SP), pp. 739–753. IEEE, 2019.
[22] Oja, E. Simplified neuron model as a principal component analyzer.Journal of mathematical
biology, 15:267–273, 1982.
[23] Polyak, B. T. Gradient methods for minimizing functionals.Zhurnal vychislitel’noi matematiki
i matematicheskoi fiziki, 3(4):643–653, 1963.
[24] Reddi, S. J., Charles, Z., Zaheer, M., Garrett, Z., Rush, K., Kone ˇcn`y, J., Kumar, S., and
McMahan, H. B. Adaptive federated optimization. InInternational Conference on Learning
Representations, 2021.
[25] Sen, P., Namata, G., Bilgic, M., Getoor, L., Galligher, B., and Eliassi-Rad, T. Collective
classification in network data.AI magazine, 29(3):93–93, 2008.
[26] Shchur, O., Mumme, M., Bojchevski, A., and Günnemann, S. Pitfalls of graph neural network
evaluation.arXiv preprint arXiv:1811.05868, 2018.
[27] Shokri, R., Stronati, M., Song, C., and Shmatikov, V . Membership inference attacks against
machine learning models. In2017 IEEE symposium on security and privacy (SP), pp. 3–18.
IEEE, 2017.
[28] Suzumura, T., Zhou, Y ., Baracaldo, N., Ye, G., Houck, K., Kawahara, R., Anwar, A., Stavarache,
L. L., Watanabe, Y ., Loyola, P., et al. Towards federated graph learning for collaborative
financial crimes detection.arXiv preprint arXiv:1909.12946, 2019.
[29] Tan, A. Z., Yu, H., Cui, L., and Yang, Q. Towards personalized federated learning.IEEE
transactions on neural networks and learning systems, 34(12):9587–9603, 2022.
[30] Tan, Y ., Liu, Y ., Long, G., Jiang, J., Lu, Q., and Zhang, C. Federated learning on non-iid
graphs via structural knowledge sharing. InProceedings of the AAAI conference on artificial
intelligence, 2023.
[31] Tan, Z., Wan, G., Huang, W., and Ye, M. Fedssp: Federated graph learning with spectral
knowledge and personalized preference.Advances in Neural Information Processing Systems,
37:34561–34581, 2024.
[32] Wang, B., Li, A., Pang, M., Li, H., and Chen, Y . Graphfl: A federated learning framework for
semi-supervised node classification on graphs. In2022 IEEE International Conference on Data
Mining (ICDM), pp. 498–507. IEEE, 2022.
[33] Wang, J., Liu, Q., Liang, H., Joshi, G., and Poor, H. V . Tackling the objective inconsistency
problem in heterogeneous federated optimization.Advances in neural information processing
systems, 33:7611–7623, 2020.
[34] Wu, C., Wu, F., Cao, Y ., Huang, Y ., and Xie, X. Fedgnn: Federated graph neural network for
privacy-preserving recommendation.arXiv preprint arXiv:2102.04925, 2021.
12

## Page 13

[35] Xie, H., Ma, J., Xiong, L., and Yang, C. Federated graph classification over non-iid graphs. In
Thirty-Fifth Conference on Neural Information Processing Systems, 2021.
[36] Xie, H., Xiong, L., and Yang, C. Federated node classification over graphs with latent link-type
heterogeneity. InProceedings of the ACM Web Conference 2023, pp. 556–566, 2023.
[37] Yao, Y ., Jin, W., Ravi, S., and Joe-Wong, C. Fedgcn: convergence-communication tradeoffs in
federated training of graph convolutional networks.Advances in neural information processing
systems, 2023.
[38] Ye, R., Ni, Z., Wu, F., Chen, S., and Wang, Y . Personalized federated learning with inferred
collaboration graphs. InInternational Conference on Machine Learning, pp. 39801–39817.
PMLR, 2023.
[39] Yue, L., Liu, Q., Gao, W., Liu, Y ., Zhang, K., Du, Y ., Wang, L., and Yao, F. Federated self-
explaining gnns with anti-shortcut augmentations. InForty-first International Conference on
Machine Learning, 2024.
[40] Zhang, K., Yang, C., Li, X., Sun, L., and Yiu, S. M. Subgraph federated learning with missing
neighbor generation.Advances in Neural Information Processing Systems, 34:6671–6682, 2021.
[41] Zhang, T., Mai, C., Chang, Y ., Chen, C., Shu, L., and Zheng, Z. Fedego: privacy-preserving
personalized federated graph learning with ego-graphs.ACM Transactions on Knowledge
Discovery from Data, 18(2):1–27, 2023.
[42] Zhang, Z., Hu, Q., Yu, Y ., Gao, W., and Liu, Q. Fedgt: federated node classification with
scalable graph transformer.arXiv preprint arXiv:2401.15203, 2024.
[43] Zhao, Y ., Li, M., Lai, L., Suda, N., Civin, D., and Chandra, V . Federated learning with non-iid
data.arXiv preprint arXiv:1806.00582, 2018.
[44] Zhuo, W. and Tan, G. Efficient graph similarity computation with alignment regularization.
Advances in Neural Information Processing Systems, 35:30181–30193, 2022.
[45] Zhuo, W., Liu, Z., Hooi, B., He, B., Tan, G., Fathony, R., and Chen, J. Partitioning message
passing for graph fraud detection. InThe Twelfth International Conference on Learning
Representations, 2024. URLhttps://openreview.net/forum?id=tEgrUrUuwA.
[46] Zhuo, W., Yu, H., Tan, G., and Li, X. Commute graph neural networks. InForty-second
International Conference on Machine Learning, 2025. URL https://openreview.net/
forum?id=29Leye951l.
13

## Page 14

NeurIPS Paper Checklist
1.Claims
Question: Do the main claims made in the abstract and introduction accurately reflect the
paper’s contributions and scope?
Answer: [Yes] .
Justification: In the abstract and Introduction, we have highlighted the contributions of our
work, such as lines 54 - 70.
Guidelines:
•The answer NA means that the abstract and introduction do not include the claims
made in the paper.
•The abstract and/or introduction should clearly state the claims made, including the
contributions made in the paper and important assumptions and limitations. A No or
NA answer to this question will not be perceived well by the reviewers.
•The claims made should match theoretical and experimental results, and reflect how
much the results can be expected to generalize to other settings.
•It is fine to include aspirational goals as motivation as long as it is clear that these goals
are not attained by the paper.
2.Limitations
Question: Does the paper discuss the limitations of the work performed by the authors?
Answer: [Yes] .
Justification: See Appendix F.
Guidelines:
•The answer NA means that the paper has no limitation while the answer No means that
the paper has limitations, but those are not discussed in the paper.
• The authors are encouraged to create a separate "Limitations" section in their paper.
•The paper should point out any strong assumptions and how robust the results are to
violations of these assumptions (e.g., independence assumptions, noiseless settings,
model well-specification, asymptotic approximations only holding locally). The authors
should reflect on how these assumptions might be violated in practice and what the
implications would be.
•The authors should reflect on the scope of the claims made, e.g., if the approach was
only tested on a few datasets or with a few runs. In general, empirical results often
depend on implicit assumptions, which should be articulated.
•The authors should reflect on the factors that influence the performance of the approach.
For example, a facial recognition algorithm may perform poorly when image resolution
is low or images are taken in low lighting. Or a speech-to-text system might not be
used reliably to provide closed captions for online lectures because it fails to handle
technical jargon.
•The authors should discuss the computational efficiency of the proposed algorithms
and how they scale with dataset size.
•If applicable, the authors should discuss possible limitations of their approach to
address problems of privacy and fairness.
•While the authors might fear that complete honesty about limitations might be used by
reviewers as grounds for rejection, a worse outcome might be that reviewers discover
limitations that aren’t acknowledged in the paper. The authors should use their best
judgment and recognize that individual actions in favor of transparency play an impor-
tant role in developing norms that preserve the integrity of the community. Reviewers
will be specifically instructed to not penalize honesty concerning limitations.
3.Theory assumptions and proofs
Question: For each theoretical result, does the paper provide the full set of assumptions and
a complete (and correct) proof?
Answer: [Yes] .
14

## Page 15

Justification: All theorems are in Section 3.3. All assumptions and proofs are shown in
Appendix C.
Guidelines:
• The answer NA means that the paper does not include theoretical results.
•All the theorems, formulas, and proofs in the paper should be numbered and cross-
referenced.
•All assumptions should be clearly stated or referenced in the statement of any theorems.
•The proofs can either appear in the main paper or the supplemental material, but if
they appear in the supplemental material, the authors are encouraged to provide a short
proof sketch to provide intuition.
•Inversely, any informal proof provided in the core of the paper should be complemented
by formal proofs provided in appendix or supplemental material.
• Theorems and Lemmas that the proof relies upon should be properly referenced.
4.Experimental result reproducibility
Question: Does the paper fully disclose all the information needed to reproduce the main ex-
perimental results of the paper to the extent that it affects the main claims and/or conclusions
of the paper (regardless of whether the code and data are provided or not)?
Answer: [Yes] .
Justification: We provide the implementation details in Appendix D. Besides, we provide
the source code of our work.
Guidelines:
• The answer NA means that the paper does not include experiments.
•If the paper includes experiments, a No answer to this question will not be perceived
well by the reviewers: Making the paper reproducible is important, regardless of
whether the code and data are provided or not.
•If the contribution is a dataset and/or model, the authors should describe the steps taken
to make their results reproducible or verifiable.
•Depending on the contribution, reproducibility can be accomplished in various ways.
For example, if the contribution is a novel architecture, describing the architecture fully
might suffice, or if the contribution is a specific model and empirical evaluation, it may
be necessary to either make it possible for others to replicate the model with the same
dataset, or provide access to the model. In general. releasing code and data is often
one good way to accomplish this, but reproducibility can also be provided via detailed
instructions for how to replicate the results, access to a hosted model (e.g., in the case
of a large language model), releasing of a model checkpoint, or other means that are
appropriate to the research performed.
•While NeurIPS does not require releasing code, the conference does require all submis-
sions to provide some reasonable avenue for reproducibility, which may depend on the
nature of the contribution. For example
(a)If the contribution is primarily a new algorithm, the paper should make it clear how
to reproduce that algorithm.
(b)If the contribution is primarily a new model architecture, the paper should describe
the architecture clearly and fully.
(c)If the contribution is a new model (e.g., a large language model), then there should
either be a way to access this model for reproducing the results or a way to reproduce
the model (e.g., with an open-source dataset or instructions for how to construct
the dataset).
(d)We recognize that reproducibility may be tricky in some cases, in which case
authors are welcome to describe the particular way they provide for reproducibility.
In the case of closed-source models, it may be that access to the model is limited in
some way (e.g., to registered users), but it should be possible for other researchers
to have some path to reproducing or verifying the results.
5.Open access to data and code
15

## Page 16

Question: Does the paper provide open access to the data and code, with sufficient instruc-
tions to faithfully reproduce the main experimental results, as described in supplemental
material?
Answer: [Yes] .
Justification: We have added the link to the source code of our work. Besides, we provide a
detailed README file to reproduce our experimental results.
Guidelines:
• The answer NA means that paper does not include experiments requiring code.
•Please see the NeurIPS code and data submission guidelines ( https://nips.cc/
public/guides/CodeSubmissionPolicy) for more details.
•While we encourage the release of code and data, we understand that this might not be
possible, so “No” is an acceptable answer. Papers cannot be rejected simply for not
including code, unless this is central to the contribution (e.g., for a new open-source
benchmark).
•The instructions should contain the exact command and environment needed to run to
reproduce the results. See the NeurIPS code and data submission guidelines ( https:
//nips.cc/public/guides/CodeSubmissionPolicy) for more details.
•The authors should provide instructions on data access and preparation, including how
to access the raw data, preprocessed data, intermediate data, and generated data, etc.
•The authors should provide scripts to reproduce all experimental results for the new
proposed method and baselines. If only a subset of experiments are reproducible, they
should state which ones are omitted from the script and why.
•At submission time, to preserve anonymity, the authors should release anonymized
versions (if applicable).
•Providing as much information as possible in supplemental material (appended to the
paper) is recommended, but including URLs to data and code is permitted.
6.Experimental setting/details
Question: Does the paper specify all the training and test details (e.g., data splits, hyper-
parameters, how they were chosen, type of optimizer, etc.) necessary to understand the
results?
Answer: [Yes] .
Justification: See Appendix D.
Guidelines:
• The answer NA means that the paper does not include experiments.
•The experimental setting should be presented in the core of the paper to a level of detail
that is necessary to appreciate the results and make sense of them.
•The full details can be provided either with the code, in appendix, or as supplemental
material.
7.Experiment statistical significance
Question: Does the paper report error bars suitably and correctly defined or other appropriate
information about the statistical significance of the experiments?
Answer: [Yes] .
Justification: See Table 1.
Guidelines:
• The answer NA means that the paper does not include experiments.
•The authors should answer "Yes" if the results are accompanied by error bars, confi-
dence intervals, or statistical significance tests, at least for the experiments that support
the main claims of the paper.
•The factors of variability that the error bars are capturing should be clearly stated (for
example, train/test split, initialization, random drawing of some parameter, or overall
run with given experimental conditions).
16

## Page 17

•The method for calculating the error bars should be explained (closed form formula,
call to a library function, bootstrap, etc.)
• The assumptions made should be given (e.g., Normally distributed errors).
•It should be clear whether the error bar is the standard deviation or the standard error
of the mean.
•It is OK to report 1-sigma error bars, but one should state it. The authors should
preferably report a 2-sigma error bar than state that they have a 96% CI, if the hypothesis
of Normality of errors is not verified.
•For asymmetric distributions, the authors should be careful not to show in tables or
figures symmetric error bars that would yield results that are out of range (e.g. negative
error rates).
•If error bars are reported in tables or plots, The authors should explain in the text how
they were calculated and reference the corresponding figures or tables in the text.
8.Experiments compute resources
Question: For each experiment, does the paper provide sufficient information on the com-
puter resources (type of compute workers, memory, time of execution) needed to reproduce
the experiments?
Answer: [Yes] .
Justification: See Appendix D.
Guidelines:
• The answer NA means that the paper does not include experiments.
•The paper should indicate the type of compute workers CPU or GPU, internal cluster,
or cloud provider, including relevant memory and storage.
•The paper should provide the amount of compute required for each of the individual
experimental runs as well as estimate the total compute.
•The paper should disclose whether the full research project required more compute
than the experiments reported in the paper (e.g., preliminary or failed experiments that
didn’t make it into the paper).
9.Code of ethics
Question: Does the research conducted in the paper conform, in every respect, with the
NeurIPS Code of Ethicshttps://neurips.cc/public/EthicsGuidelines?
Answer: [Yes] .
Justification: Our research conforms with the NeurIPS Code of Ethics.
Guidelines:
•The answer NA means that the authors have not reviewed the NeurIPS Code of Ethics.
•If the authors answer No, they should explain the special circumstances that require a
deviation from the Code of Ethics.
•The authors should make sure to preserve anonymity (e.g., if there is a special consid-
eration due to laws or regulations in their jurisdiction).
10.Broader impacts
Question: Does the paper discuss both potential positive societal impacts and negative
societal impacts of the work performed?
Answer: [NA] .
Justification: There are no negative societal impacts of our work.
Guidelines:
• The answer NA means that there is no societal impact of the work performed.
•If the authors answer NA or No, they should explain why their work has no societal
impact or why the paper does not address societal impact.
•Examples of negative societal impacts include potential malicious or unintended uses
(e.g., disinformation, generating fake profiles, surveillance), fairness considerations
(e.g., deployment of technologies that could make decisions that unfairly impact specific
groups), privacy considerations, and security considerations.
17

## Page 18

•The conference expects that many papers will be foundational research and not tied
to particular applications, let alone deployments. However, if there is a direct path to
any negative applications, the authors should point it out. For example, it is legitimate
to point out that an improvement in the quality of generative models could be used to
generate deepfakes for disinformation. On the other hand, it is not needed to point out
that a generic algorithm for optimizing neural networks could enable people to train
models that generate Deepfakes faster.
•The authors should consider possible harms that could arise when the technology is
being used as intended and functioning correctly, harms that could arise when the
technology is being used as intended but gives incorrect results, and harms following
from (intentional or unintentional) misuse of the technology.
•If there are negative societal impacts, the authors could also discuss possible mitigation
strategies (e.g., gated release of models, providing defenses in addition to attacks,
mechanisms for monitoring misuse, mechanisms to monitor how a system learns from
feedback over time, improving the efficiency and accessibility of ML).
11.Safeguards
Question: Does the paper describe safeguards that have been put in place for responsible
release of data or models that have a high risk for misuse (e.g., pretrained language models,
image generators, or scraped datasets)?
Answer: [NA] .
Justification: No risks.
Guidelines:
• The answer NA means that the paper poses no such risks.
•Released models that have a high risk for misuse or dual-use should be released with
necessary safeguards to allow for controlled use of the model, for example by requiring
that users adhere to usage guidelines or restrictions to access the model or implementing
safety filters.
•Datasets that have been scraped from the Internet could pose safety risks. The authors
should describe how they avoided releasing unsafe images.
•We recognize that providing effective safeguards is challenging, and many papers do
not require this, but we encourage authors to take this into account and make a best
faith effort.
12.Licenses for existing assets
Question: Are the creators or original owners of assets (e.g., code, data, models), used in
the paper, properly credited and are the license and terms of use explicitly mentioned and
properly respected?
Answer: [Yes] .
Justification: All datasets used in this paper are public, and we have properly cited the
original paper.
Guidelines:
• The answer NA means that the paper does not use existing assets.
• The authors should cite the original paper that produced the code package or dataset.
•The authors should state which version of the asset is used and, if possible, include a
URL.
• The name of the license (e.g., CC-BY 4.0) should be included for each asset.
•For scraped data from a particular source (e.g., website), the copyright and terms of
service of that source should be provided.
•If assets are released, the license, copyright information, and terms of use in the
package should be provided. For popular datasets, paperswithcode.com/datasets
has curated licenses for some datasets. Their licensing guide can help determine the
license of a dataset.
•For existing datasets that are re-packaged, both the original license and the license of
the derived asset (if it has changed) should be provided.
18

## Page 19

•If this information is not available online, the authors are encouraged to reach out to
the asset’s creators.
13.New assets
Question: Are new assets introduced in the paper well documented and is the documentation
provided alongside the assets?
Answer: [NA] .
Justification: The paper does not release new assets.
Guidelines:
• The answer NA means that the paper does not release new assets.
•Researchers should communicate the details of the dataset/code/model as part of their
submissions via structured templates. This includes details about training, license,
limitations, etc.
•The paper should discuss whether and how consent was obtained from people whose
asset is used.
•At submission time, remember to anonymize your assets (if applicable). You can either
create an anonymized URL or include an anonymized zip file.
14.Crowdsourcing and research with human subjects
Question: For crowdsourcing experiments and research with human subjects, does the paper
include the full text of instructions given to participants and screenshots, if applicable, as
well as details about compensation (if any)?
Answer: [NA] .
Justification: The paper does not involve crowdsourcing nor research with human subjects.
Guidelines:
•The answer NA means that the paper does not involve crowdsourcing nor research with
human subjects.
•Including this information in the supplemental material is fine, but if the main contribu-
tion of the paper involves human subjects, then as much detail as possible should be
included in the main paper.
•According to the NeurIPS Code of Ethics, workers involved in data collection, curation,
or other labor should be paid at least the minimum wage in the country of the data
collector.
15.Institutional review board (IRB) approvals or equivalent for research with human
subjects
Question: Does the paper describe potential risks incurred by study participants, whether
such risks were disclosed to the subjects, and whether Institutional Review Board (IRB)
approvals (or an equivalent approval/review based on the requirements of your country or
institution) were obtained?
Answer: [NA] .
Justification: The paper does not involve crowdsourcing nor research with human subjects.
Guidelines:
•The answer NA means that the paper does not involve crowdsourcing nor research with
human subjects.
•Depending on the country in which research is conducted, IRB approval (or equivalent)
may be required for any human subjects research. If you obtained IRB approval, you
should clearly state this in the paper.
•We recognize that the procedures for this may vary significantly between institutions
and locations, and we expect authors to adhere to the NeurIPS Code of Ethics and the
guidelines for their institution.
•For initial submissions, do not include any information that would break anonymity (if
applicable), such as the institution conducting the review.
16.Declaration of LLM usage
19

## Page 20

Question: Does the paper describe the usage of LLMs if it is an important, original, or
non-standard component of the core methods in this research? Note that if the LLM is used
only for writing, editing, or formatting purposes and does not impact the core methodology,
scientific rigorousness, or originality of the research, declaration is not required.
Answer: [NA] .
Justification: The core method development in this research does not involve LLMs as any
important, original, or non-standard components.
Guidelines:
•The answer NA means that the core method development in this research does not
involve LLMs as any important, original, or non-standard components.
•Please refer to our LLM policy ( https://neurips.cc/Conferences/2025/LLM )
for what should or should not be described.
20

## Page 21

A More Discussion of Related Work
In subgraph federated learning, each client holds a local subgraph Gkof a global graph G. These
subgraphs can vary substantially in their feature distributions, structural/topological properties, and
label distributions. Thus, simply applying FedAvg may fail to converge properly or yield a suboptimal
global model, because clients often learn different parameters tailored to their local subgraphs,
and blindly averaging those parameters disregards the non-IID nature of the data. To address this,
recent studies move beyond basic FedAvg by introducing personalized or locality-aware aggregation
schemes that better handle heterogeneous subgraph data.
GCFL [ 35] compares each client’s parameter updates before and after communication. If a client’s
update deviates substantially from the majority, it is deemed too different and is excluded from
the dominant aggregation cluster. However, GCFL relies on hard clustering, which cannot capture
finer-grained similarities across clients. Moreover, it depends on manually tuned hyperparameters to
control how different a client must be before exclusion, leaving it unclear how large a deviation is
tolerable without enough knowledge about the raw data. FED-PUB [ 3], on the other hand, constructs
a proxy graph at the server and evaluates model outputs from each client on the proxy graph to
measure their similarity. Clients with similar outputs on the proxy graph are deemed more alike and
thus aggregated more closely. Yet building a suitable proxy graph as the middleware to measure
the similarity between clients is nontrivial, because it requires simulating the real graph data on the
server.
In this work, we propose an orthogonal approach to measure and aggregate models on the server.
Specifically, beyond distributing a global GNN, the server also provides a global Auxiliary Projection
Vector ( APV) to each client at the start of every communication round, as shown on the left of Fig. 1.
During local training, the APV is jointly optimized with the client’s GNN parameters to form a
one-dimensional space onto which node embeddings are projected. This procedure tailors the APV,
which adjusts the shape of this space, to the unique distribution of each subgraph by preserving its
distinctive patterns. Once training concludes, clients upload their updated GNN parameters and local
APVto the server, which then compares these learned APVs to gauge similarity and detect finer-grained,
continuous heterogeneity across clients. By discarding the hard clustering thresholds used in GCFL
and removing the need for a proxy dataset used in FED-PUB, our method offers a more flexible and
efficient strategy to identify and aggregate similar subgraphs.
Another advantage of our method lies in its privacy-preserving design. We argue that sharing detailed
node embeddings, as in FedGCN [ 37], can leak private subgraph information, as adversaries on
the server could compute pairwise similarities among embeddings to reconstruct local connectivity.
Moreover, due to high dimensionality and lack of explicit structural encoding, directly comparing
parameter matrices to measure raw data similarity is both unreliable and computationally unstable. In
contrast, our proposed APVis a compact parameter vector that preserves essential node relationships
without exposing the actual node embeddings, offering stronger privacy guarantees and structure-
awareness. Additionally, its low-dimensional nature makes similarity computation more efficient and
robust.
B Pseudo Code ofFedAux
The overall training algorithm is shown in Algorithm 1.
C Proofs
C.1 Proof of Theorem 3.1
The proof relies on two mild structural assumptions, both typical in optimization analyses of deep
models.
Assumption C.1(Centred embeddings). ¯h:=1
NP
ihi=0, where Nis the number of nodes in the
current client.
Assumption C.2(Linear classifier Jacobian).Let gi:=∇ ziL(θ,a) . Assuming that the mapping
zi7→giis linear:g i=Wz ifor some matrixW∈Rd′×d′.
21

## Page 22

Algorithm 1:FedAux: Subgraph FL with Differentiable Auxiliary Projections
Input: number of clients K; global communication rounds T; local steps per round Q; learning
ratesη; similarity temperatureα
Init:server initializes global GNN weightsθ(0)andAPVa(0)∼ N(0, I d′); each clientG ksets
θ(0)
k←θ(0),a(0)
k←a(0)
1fort←1toTdo
// Server−→Clients
2broadcast{(θ(t−1)
k,a(t−1)
k)}K
k=1to each client{G k}K
k=1;
// Local training on each clientG k(runs in parallel)
3foreach clientG k∈{G 1, . . . , G K}do in parallel
4(θ k,ak)←(θ(t−1)
k,a(t−1)
k);
5forq←1toQdo
6run local GNN forward pass withh(t−1)
k,i=fθ(t−1)
k(vi)to learn node embeddings as
Eq. (1);
7compute similarity scoress(t−1)
kwiths(t−1)
k,i=⟨ˆh(t−1)
k,i,a(t−1)
k⟩;
8compute kernel weightsκ(s(t−1)
k,i, s(t−1)
k,j);
9compute kernel-based aggregated embeddingsz(t−1)
k,iwith Eq. (6);
10concatenater(t−1)
k,i= [h(t−1)
k,i∥z(t−1)
k,i];
11forward through the classifier; compute lossL CE;
12update(θ(t−1)
k,a(t−1)
k)w.r.t.L CEwith learning rateη;
13end
14upload(θ(t−1)
k,a(t−1)
k)to server;
15end
// Server-side personalised aggregation
16computew(t−1)
k,lwith Eq. (7);
17foreach clientG kdo
18θ(t)
k←PK
l=1w(t−1)
k,lθ(t−1)
l;
19a(t)
k←PK
l=1w(t−1)
k,la(t−1)
l;
20end
21send(θ(t)
k,a(t)
k)back to clientG k;
22end
Output:personalized models
θ(T)
k,a(T)
k	K
k=1forKclients
Theorem C.2 holds exactly for a linear -softmax classifier and is a first -order approximation for MLPs.
Then we introduce the auxiliary lemmata.
Lemma C.3(Gradient of similarity score).For nodev i,∂si
∂a=hi−siaholds.
Proof.s i=a⊤hi, with∥a∥= 1 . Hence∂si
∂a=hi. Because we will always re -project aon the unit
sphere after every update, the tangential component hi−siais the effective gradient, and the radial
component vanishes.
Lemma C.4(Gradient of kernel entry).∂Kij
∂a=−2
σ2(si−sj)Kij[(hi−hj)−(s i−sj)a].
Proof. Apply the chain rule to Kij=κ(s i, sj) = exp
−1
σ2(si−sj)2
and invoke Theorem C.3
for∂(s i−sj)/∂a.
Lemma C.5(Gradient of the kernel-smoothed embedding).Define the normalized kernel weights:
βij:=Kij
Mi,X
jβij= 1.(13)
22

## Page 23

Then we have
∂zi
∂a=−2
σ2NX
j=1βij(si−sj) (hj−zi)⊗[(h i−hj)−(s i−sj)a],(14)
where⊗denotes the outer product.
Proof. LetDi=PN
j=1Kijhj, based on Eq. (6) we have zi=Di
Mi. Using the quotient rule, we have:
∂zi
∂a=1
Mi∂Di
∂a−Di
M2
i∂Mi
∂a.(15)
Then we compute the two gradients in Eq. (15). The gradient of the Diw.r.t. ais∂Di
∂a=PN
j=1∂Kij
∂ah⊤
j, where∂Kij
∂ahas been given by Theorem C.4. Thus we have:
∂Di
∂a=−2
σ2NX
j=1(si−sj)Kijhj[(hi−hj)−(s i−sj)a]⊤.(16)
The Gradient ofM ican be represented as:
∂Mi
∂a=NX
j=1∂Kij
∂a=−2
σ2NX
j=1(si−sj)Kij[(hi−hj)−(s i−sj)a].(17)
We can substitute Eq. (16) and Eq. (17) into the quotient rule Eq. (15):
∂zi
∂a=−2
σ21
MiNX
j=1(si−sj)Kijhj[(hi−hj)−(s i−sj)a]⊤
+2
σ21
M2
i
NX
j=1Kijhj
 NX
ℓ=1(si−sℓ)Kiℓ[(hi−hℓ)−(s i−sℓ)a]⊤!
.(18)
Given Eq. (13), Eq. (18) can be rewritten as:
∂zi
∂a=−2
σ2NX
j=1βij(si−sj)hj[(hi−hj)−(s i−sj)a]⊤
+2
σ2
NX
j=1βijhj

|{z}
zi NX
ℓ=1βiℓ(si−sℓ) [(h i−hℓ)−(s i−sℓ)a]⊤!
.(19)
By re-indexingℓ→j, Eq. (19) can be represented as:
∂zi
∂a=−2
σ2NX
j=1βij(si−sj) (hj−zi) [(h i−hj)−(s i−sj)a]⊤,(20)
which is exactly the Eq. (14), completing the derivation.
C.1.1 Proof of Theorem 3.1
Proof.Using Theorem C.2 and Theorem C.5, we can perform chain-rule expansion of∇ aLas:
∇aL=1
NNX
i=1∂zi
∂a⊤
gi=1
NNX
i=1NX
j=1∂zi
∂a⊤
Wzi.(21)
Substituting Eq. (14) into Eq. (21) gives:
∇aL=−2
Nσ2NX
i=1NX
j=1βij(si−sj) [(h i−hj)−(s i−sj)a] (h j−zi)⊤Wzi.(22)
23

## Page 24

For small σ,βijis sharply peaked at j=i . Given εij:=s i−sj, since βij≤e−ε2
ij/σ2, all terms
withj̸=i are exponentially suppressed, and the dominant contribution arises from the linearization
aroundε ij= 0. Then we conduct Taylor expansion to first order inε ij:
∇aL=−2
Nσ2NX
i=1NX
j=1
βijεijhi 
h⊤
iWh i
+O 
σ0
.(23)
In Big-O notation, the symbol O(σµ)asσ→0+means that there exists a constant c >0 and a
neighbourhood (0, σ 0]such that |O(σµ)| ≤cσµ. Using Theorem C.1 and symmetry of the inner
summation one obtains the compact matrix form of the above formula:
∇aL=−2
σ2 
1
NNX
i=1hih⊤
i!
a+R(σ) =−2
σ2Ca+R(σ),(24)
with∥R(σ)∥=O 
σ0
. This proves Eq. (9).
Since ais re-normalised after every update, the effective tangential gradient [ 7] is∇aL−(a⊤∇aL)a.
Note that a⊤Cais scalar, so subtracting the radial part yields the tangential gradient −Ca+  
a⊤Ca
a. A projected gradient descent step with learning rateηtherefore becomes:
a←Π Sd−1 
a−η
Ca− 
a⊤Ca
a
= Π Sd−1((I−ηC)a),(25)
which is exactly the discrete-time Oja [22] update Eq. (10).
Letλmaxbe the largest eigenvalue of C, with unit-norm eigenvector umax. Standard theory of Oja’s
algorithm [13, 22] states:
• Every eigenvector ofCis a fixed point of Eq. (10).
•All eigenvectors other than ±umaxare unstable, and ±umaxare globally asymptotically
stable provided0< η <2/λ max.
Hence gradient descent drives atoward ±umax. Because the kernel and the classifier do not depend
on the sign ofa, both directions are equivalent, and choosing the positive-projection suffices.
C.1.2 Interpretation of Theorem 3.1
Rayleigh -quotient maximizationOja learning rule is a stochastic gradient ascent on the Rayleigh
quotient R(a) =a⊤Caover the unit sphere. Theorem 3.1 therefore formalizes the intuition that the
APValigns with thedirection of maximum embedding variance.
Role of the bandwidth σThe leading term Eq. (10) is multiplied by 1/σ2. A smaller bandwidth
increases the gradient magnitude, accelerating alignment but reducing smoothness; conversely, a
largerσslows convergence while preserving differentiability.
Compatibility with the global optimizationOnce the APVconverges to umax, the kernel weights
Kijdepend only on ⟨hi, umax⟩ − ⟨h j, umax⟩, which maximally separates nodes along the most
informative one-dimensional projection. This precisely captures the fidelity property we desire.
C.2 Proof of Theorem 3.2
The proof is based on three lemmata.
Lemma C.6(Weight concentration).For each rowiof the kernel matrixK, we have:
lim
σ→0+Kij=δij,(26)
whereδ ijis the Kronecker delta.
24

## Page 25

Proof.Since all scores are distinct, setting∆ i:= min j̸=i|si−sj|>0. Forj̸=iwe have:
Kij
Kii= exp
−
(si−sj)2−0
σ2
≤exp
−∆2
i
σ2
.(27)
Hence for all j̸=i ,Kij≤e−∆2
i/σ2→0 asσ→0+. Since each row of Kis a probability
distribution, the diagonal entry must satisfyK ii= 1−P
j̸=iKij→1.
Lemma C.7(Pointwise convergence of smoothed embeddings).
lim
σ→0+zi=hi,∀i= 1, . . . , N(28)
Proof.We can rewritez ias:
zi=NX
j=1αijhj=K iihi+X
j̸=iKijhj.(29)
By Theorem C.6 the non-diagonal weights vanish andK ii→1. Thereforez i→h i.
Lemma C.8(Matrix convergence in Frobenius norm).
lim
σ→0+eZ−eH
F= 0.(30)
Proof. Note that both matrices eZandeHhave the same ordering πof rows. From Theorem C.7 each
corresponding row converges aszπ(t)−hπ(t)
2→0 for every t. Since Nis finite, the Frobenius
norm also converges to 0.
C.2.1 Proof of Theorem 3.2
Proof. TheConv1D operator ConvWis linear and its Lipschitz constant with respect to the Frobe-
nius norm is LIP W=PB
τ=1∥Wτ∥2
21/2
, then for any two sequencesXandYwe have:
∥ConvW(X)−Conv W(Y)∥F≤LIPW∥X − Y∥ F.(31)
Applying this bound withX= eZandY= eHyields:
ConvW(eZ)−Conv W(eH)
F≤LIPW∥eZ−eH∥F.(32)
Theorem C.8 states that the right -hand side of Eq. (32) converges to 0, thus the left -hand side must
converge to zero as well, establishing the claimed limit.
C.3 Proof of Theorem 3.3
C.3.1 Local Training Analysis
For a client Gkat any communication round and inner step q∈ {1,···, Q} , letΨq
k:= (θq
k,aq
k)at
any communication round. Given the assumption that the local objective Lkis differentiable and
L-smooth: ∀Ψk,Ψ′
k:∥∇L k(Ψk)− ∇L k(Ψ′
k)∥ ≤L∥Ψ k−Ψ′
k∥, where the smoothness holds for
cross-entropy composed with neural networks whose activations are Lipschitz, we have:
Lk(Ψ′
k)≤ L k(Ψk) +⟨∇L k(Ψk),Ψ′
k−Ψ k⟩+L
2∥Ψ′
k−Ψ k∥2,∀Ψ k,Ψ′
k.(33)
TakeΨ k= Ψs−1
k, andΨ′
k= Ψq
k= Ψq−1
k−ηgq−1
k:
Lk(Ψq
k)≤ L k
Ψq−1
k
−ηD
∇Lk
Ψq−1
k
, gq−1
kE
+Lη2
2gq−1
k2
.(34)
Due to the unbiasedness assumption, i.e.,E[g k] =∇L k, we have:
E[⟨∇L k, gs
k⟩] =⟨∇L k,E[gq
k]⟩=∥∇L k∥2.(35)
25

## Page 26

Also by the bounded-variance assumption, i.e.,E qh
∥gk− ∇L k∥2i
≤ζ2, we have:
Eqh
∥gq
k∥2i
=∥∇L k∥2+Eh
∥gq
k− ∇L k∥2iAss.2
≤ ∥∇L k∥2+ζ2.(36)
Then we can insert Eq. (35) and Eq. (36) into Eq. (34) and take expectation as follows:
Eq[Lk(Ψq
k)]≤ L k
Ψq−1
k
−η∇Lk(Ψq−1
k)2
+Lη2
2∇Lk(Ψq−1
k)2
+ζ2
=Lk
Ψq−1
k
−
η−Lη2
2
∥∇L k∥2+Lη2ζ2
2.(37)
Becauseη≤1/2Lwe have1−Lη/2≥1/2, hence:
Eq[Lk(Ψq
k)]≤ L k
Ψq−1
k
−η
2∇Lk
Ψq−1
k2
+Lη2ζ2
2.(38)
Based on the assumption that each local objective Lksatisfies the µ-PL2(Polyak-Lojasiewicz)
condition [23] iff∇Lk(Ψq−1
k)2
≥2µ
Lk(Ψq−1
k)− L⋆
k
.(39)
Plug Eq. (39) into Eq. (38):
Eq[Lk(Ψq
k)− L⋆
k]≤(1−ηµ)
Lk
Ψq−1
k
− L⋆
k
+Lη2ζ2
2.(40)
We define the gap as ∆q−1
k:=L k(Ψq−1
k)− L⋆
k. Taking the total expectation and iterating Eq. (40) Q
times, we have:
Eh
∆Q
ki
≤(1−ηµ)Q∆1
k+Lη2ζ2
2QX
j=1(1−ηµ)j−1.(41)
The geometric sum is:
QX
j=1(1−ηµ)j−1=1−(1−ηµ)Q
ηµ≤1
ηµ.(42)
Therefore, the following inequality holds:
Eh
∆Q
ki
≤(1−ηµ)Q∆1
k+ηLζ2
2µ,(43)
which is the per-client local-training contraction.
C.3.2 Effect of Global Kernel-Based Aggregation
Define Ψloc,(t−1)
k:= ΨQ
kwhich means the local client parameters after Qlocal training iterations.
Letf(t−1):=h
f(t−1)
1,···, f(t−1)
Ki⊤
, where f(t−1)
k=L k(Ψloc,(t−1)
k)− L⋆
k. Recall our proposed
personalized aggregation scheme in Eq. (8), it can be rewritten as:
Ψ(t)
k=KX
l=1w(t−1)
klΨloc,(t−1)
l.(44)
Since each new parameter is a convex combination Eq. (44), based on the Jensen’s inequality and
L-smoothness assumption in Eq. (33), the following inequality holds:
Lk(Ψ(t)
k) =KX
l=1w(t−1)
klLk(Ψloc,(t−1)
l).(45)
2Here, we slightly abuse the notation µ, which was previously introduced in Section C.1.1 with a different
meaning.
26

## Page 27

Letp= [p 1, . . . , p K]⊤, Eq. (45) subtractsL⋆
kand multiply byp k, and sum overk, we can reach:
L(Ψ(t))− L⋆≤p⊤Ω(t−1)f(t−1).(46)
Let the global average gap as ¯f(t−1):=p⊤f(t−1)andr(t−1):=f(t−1)−¯f(t−1)1. Since row-
stochasticity impliesΩ(t−1)1=1, we have:
p⊤Ω(t−1)f(t−1)=¯f(t−1)+p⊤Ω(t−1)r(t−1).(47)
Hence:
L
Ψ(t)
− L⋆≤¯f(t−1)+p⊤V(t−1)r(t−1),V(t−1):= Ω(t−1)−1
K11⊤.(48)
Note thatp⊤r(t−1)= 0by definition of ¯f(t−1). Applying Cauchy–Schwarz we have:
p⊤V(t−1)r(t−1)≤p⊤V(t−1)
2r(t−1)
2.(49)
Due to the assumption that∥V(t−1)∥2≤ρand∥p∥ 2≤1which is a probability vector, we have:
p⊤V(t−1)r(t−1)≤ρr(t−1)
2.(50)
Next bound∥r(t−1)∥2by the mean gap as:
r(t−1)2
2=X
k
f(t−1)
k−¯f(t−1)2
≤X
k
f(t−1)
k2
≤
max
kf(t−1)
kX
kf(t−1)
k
=max kf(t−1)
k
minkpk
p⊤f(t−1)
≤1
minkpk.(51)
Letc:= 1/√minkpk≤√
K, we can combine Eq. (50) and Eq. (51) to get the following inequality:
p⊤V(t−1)r(t−1)≤ρcq
¯f(t−1).(52)
Then by squaring both sides of Eq. (52) and usep¯f≤1 + ¯f, we have:
p⊤V(t−1)r(t−1)≤ρ2c2
1 +¯f(t−1)
≤2ρ2c2
1−ρ¯f(t−1),(53)
where the last inequality employs ¯f(t−1)≤(1−ρ)−1¯f(t−1)which is trivial for 0< ρ <1 . Taking
expectations, we can substitute Eq. (53) in to Eq. (48) to obtain:
Eh
L
Ψ(t)
− L⋆i
≤
1 +2ρ2
1−ρ
Eh
¯f(t−1)i
.(54)
Given Eq. (43) and ¯f(t−1)=P
kpkEh
f(t−1)
ki
, we can boundE[f(t−1)
k]by:
Eh
f(t−1)
ki
≤(1−ηµ)Q
Lk
Ψ(t−1)
k
− L⋆
k
+ηLζ2
2µ.(55)
By taking a weighted sum of the above formula over allKclients with weightsp k, we obtain:
Eh
¯f(t−1)i
≤(1−ηµ)Q
L
Ψ(t−1)
− L⋆
+ηLζ2
2µ.(56)
27

## Page 28

One-round contractionBy plugging Eq. (56) into Eq. (54), we have:
Eh
L
Ψ(t)
− L⋆i
≤(1−ηµ)Q
1 +2ρ2
1−ρ
L
Ψ(t−1)
− L⋆
+ηLζ2
2µ
1 +2ρ2
1−ρ
.
(57)
Since1 +2ρ2
1−ρ≤1 +2ρ
1−ρ=1
1−ρandρ <1, the following inequality holds:
Eh
L
Ψ(t)
− L⋆i
≤(1−ηµ)Q
L
Ψ(t−1)
− L⋆
+ηLζ2
2µ+2ηLρ2
µ(1−ρ)2,(58)
where the last term absorbs the factor from(1−ρ)−1.
Across Tcommunication roundsBy setting γ:= (1−ηµ)Qwhere 0< γ <1 , we can unroll
Eq. (58) as:
Eh
L
Ψ(T)
− L⋆i
≤γT
L
Ψ(0)
− L⋆
+ηLζ2
2µT−1X
t=0γt+2ηLρ2
µ(1−ρ)2T−1X
t=0γt.(59)
Since the geometric sums satisfyPT−1
t=0γt≤1
1−γ, while1−γ= 1−(1−ηµ)Q≥ηµ, we have:
T−1X
t=0γt≤1
ηµ.(60)
By inserting the above inequality into Eq. (59) and simplify, we can easily get:
Eh
L
Ψ(T)
− L⋆i
≤γT
L
Ψ(0)
− L⋆
+ηLζ2
2µ+2ηLρ2
µ(1−ρ)2.(61)
RecoveringγT= (1−ηµ)QTgives exactly Eq. (12) in Theorem 3.3, which concludes the proof.
D Experimental Details
D.1 Dataset Statistics
Table 4 summarizes the statistics of the datasets used in our experiments. It includes the total number
of nodes, edges, node classes, and feature dimensions for each dataset. Specifically, we use four
citation graph datasets (Cora, CiteSeer, Pubmed, and ogbn-arxiv) and two product co-purchase graph
datasets (Amazon-Computer and Amazon-Photo).
Table 4: Dataset statistics
Datasets Nodes Edges Classes Features
Cora 2,708 5,429 7 1,433
CiteSeer 3,327 4,732 6 3,703
Pubmed 19,717 44,324 3 500
Amazon-Computer 13,752 491,722 10 767
Amazon-Photo 7,650 238,162 8 745
ogbn-arxiv 169,343 2,315,598 40 128
D.2 Implementation Details
Following the standard FL settings, in our FedAux , both the local client models and the global
server model adopt the same backbone architecture. We employ MaskedGCN [ 3] to generate node
embeddings and sweep the number of GCN layers over L∈ {1,2,3} . The hidden dimension is
selected from d′∈ {64,128,256} , and dropout probabilities are set to 0.5. The auxiliary projection
vector ais initialized from a Gaussian distribution in Rd′. The similarity–temperature parameter αis
set to 10, and the bandwidth σis fixed to 1. For the FL schedule, we run T= 100 communication
rounds with Q= 1 local epoch on the smaller citation datasets (Cora, CiteSeer, Pubmed). On all
other datasets, we set the total number of rounds to T= 200 and the number of local epochs per
round to Q= 2 . All experiments are executed on a workstation equipped with an NVIDIA Tesla
V100 SXM2 GPU (32 GB) running CUDA 12.4.
28

## Page 29

Table 5: The degree of non-IIDness.
Cora CiteSeer Pubmed
Non-IIDness 5 Clients 10 Clients 20 Clients 5 Clients 10 Clients 20 Clients 5 Clients 10 Clients 20 Clients
ξ0.2667 0.3092 0.3760 0.1848 0.2292 0.2572 0.1316 0.1500 0.1725
Amazon-Computer Amazon-Photo ogbn-arxiv
Non-IIDness 5 Clients 10 Clients 20 Clients 5 Clients 10 Clients 20 Clients 5 Clients 10 Clients 20 Clients
ξ0.2774 0.3582 0.3931 0.3600 0.4314 0.4840 0.3398 0.3668 0.4307
D.3 Quantifying Non-IIDness in Federated Graph Datasets
To compare how much statistical heterogeneity (i.e., non-IIDness) each dataset induces under a given
partition scheme, it is useful to measure how far the local data distribution at each client deviates
from the global distribution and how dispersed local distributions are from one another. Below are
three complementary, fully formalized metrics that can be computed once the graph has been split
intoKclient subgraphs{G 1,···, G K}.
Label-distribution divergenceLet P(y) be the global class prior and Pk(y)the class prior in
client Gk. We use the average Jensen–Shannon (JS) divergence to measure the gap between each
local label prior and the global label prior as follows:
JSD=1
KKX
k=11
2[KL (P k∥Rk) + KL (P∥R k)],(62)
where Rk=1
2(Pk+P) denotes the mid-point distribution between PkandPwithRk(y∈Y) =
1
2[Pk(y) +P(y)] . Pinsker’s inequality [ 6] gives that JSD∈[0,log 2] . A small JSDindicates that
each client’s label distribution closely matches the global prior, so the partition is effectively IID.
As the JSDincreases, local class proportions deviate more sharply from the global mixture, making
individual clients progressively class-specific and therefore increasingly subject to statistical non-
IIDness.
Subgraph-distribution discrepancyLabel skew alone may underestimate heterogeneity when
covariate shift is strong. To quantify covariate-shift–induced heterogeneity, we measure how far
the embedding distribution of each client deviates from that of every other client in an embedding
space that reflects graph structure and attributes. We first obtain node embeddings for all nodes with
a simple neighbor aggregation Zk=A kXk={z k,i}Nk
i=1in each client. Let Zkbe the empirical
distribution of embeddings held by client Gk. We define the graph-distribution discrepancy of a
K-client partition as the mean pair-wise maximum mean discrepancy (MMD) as:
MMD=2
K(K−1)X
1≤k<l≤K1
|Vk|X
vi∈Vkϕ(zk,i)−1
|Vl|X
vj∈Vlϕ(zl,j)2
2,(63)
where ϕ(·) is the canonical feature map of a Gaussian RBF kernel with the bandwidth fixed with the
median pairwise distance to ensure comparability across datasets. Eq. (63) evaluates to zero when all
clients share an identical embedding distribution (IID) and increases monotonically with covariate
divergence.
Based on the above two perspectives, we can quantify the degree of non-IIDness by summing JSD
andMMD asξ=JSD+MMD , where a higher ξindicates a higher degree of non-IIDness. We show
the degree of non-IIDness of all datasets under different numbers of clients in Table 5.
D.4 Synthetic Graph for Client Similarity Estimation
We first generate an SBM graph with 3000 nodes that are uniformly divided into K= 20 equal-sized
blocks as clients. Inter-client edges are added with probability Pinter= 0.02 . To inject structural
non-IIDness, the 20 clients are grouped into five super-clusters {Gi}5
i=1(four clients per group). For
every client belonging to Gi, we draw intra-client edges with probability Pintra
i= 0.15×i , so clients
29

## Page 30

Table 6: Ablation studies on the federated node classification task under 10 clients.
Baseline Cora Pubmed Amazon-Computer ogbn-arxiv
(i)FedAux hard 80.29±0.7183.06±0.3588.10±1.0266.53±0.12
(ii)FedAvg mask 78.98±0.5483.97±0.5184.31±0.6065.09±0.07
FedAux 82.05±0.7185.43±0.2989.92±0.1568.50±0.27
64 128 256
d/prime1
2
3L81.26 82.53 80.38
84.57 84.49 84.01
82.10 81.37 79.55
8081828384
(a) 5 clients
64 128 256
d/prime1
2
3L78.12 78.45 78.33
80.01 81.94 82.05
78.50 79.55 80.20
79808182 (b) 10 clients
64 128 256
d/prime1
2
3L78.50 79.30 80.10
80.20 81.00 81.60
79.80 80.50 81.20
78.579.079.580.080.581.081.5 (c) 20 clients
Figure 7: Classification accuracy (%) for different GCN configurations.
within the same group are structurally IID, while clients across groups are non-IID. To inject label
and feature non-IIDness, we assign 5 labeled classes to all nodes. Nodes owned by the group Gi
receive label i−1 with high probability 0.8, and the remaining 0.2 mass is distributed uniformly
over the other four labels. Each node’s feature vector is the one-hot encoding of its label. In this
way, clients in the same group are IID in both label and feature space, while clients from different
groups exhibit pronounced distributional shifts. This controlled setting allows us to test whether
the learned APVs can cluster clients that are genuinely similar. We directly compute the similarity
between clients’ mean-pooling embeddings without considering privacy in Fig. 3a as the ground-truth
similarity. Fig. 3b-3d are similarities computed by APVs, learnable weights of the readout layer, and
functional embedding [3].
E More Experiments
E.1 Ablation Study
We conduct an ablation study in Table 6 validate our motivation and design, with the following two
ablations: (i) replacing our proposed continuous aggregation scheme over the ak-space defined in
Eq. (6) with the Conv1D operation applied on the hard-sorted embeddings as introduced by [ 18],
yielding a variant FedAux hard, and (ii) removing our server-side APV-based personalized aggregation,
instead using simple averaging to aggregate local models into a global model, leading to the baseline
FedAvg mask. Note that the FedAvg mask variant differs from the standard FedAvg used in Table 1,
where FedAvg mask adopts MaskedGCN [ 3] as the GNN backbone, whereas the standard FedAvg
utilizes a conventional GCN architecture. Compared with FedAux hard, our FedAux consistently
obtains higher accuracy. This empirical gain confirms our claim that although the hard-sorting scheme
proposed by [ 18] does allow gradient flow to optimize the APV, the underlying discrete permutation
remains non-differentiable and therefore restricts the capacity of the APVto adapt. By using our
proposed continuous aggregation with a fully differentiable kernel operator, FedAux enables smoother
gradient flow, allowing the APVand the local GNN to co-evolve optimally. Besides, FedAux and
FedAvg mask both adopt MaskedGCN as backbone, while FedAux personalized aggregates local
models based on the APVsimilarity, while FedAvg mask aggregates local models to a single global
model. Results show that FedAux outperforms FedAvg mask on all datasets, which demonstrates
that exploiting APV-based personalized aggregation allows the federation to respect non-IID data
distributions and learn more effective client-specific models.
30

## Page 31

0.1 1 10
798081828384Accuracy (%)
#Clients
5
10
20(a) Cora
0.1 1 10
85868788Accuracy (%)
#Clients
5
10
20 (b) Pubmed
0.1 1 10
87888990Accuracy (%)
#Clients
5
10
20 (c) Amazon-Computer
Figure 8: Sensitivity ofFedAuxon the similarity temperature parameterα.
E.2 Hyperparameter Analysis
Impact of Model Depth and Hidden DimensionIn our model, the number of GCN layers
is selected from L∈ {1,2,3} , and the dimension of the hidden layers is selected from d′∈
{64,128,256} . In Fig. 7, we show all the hyperparameter combinations on the Cora dataset for
different client counts. It is evident that FedAux consistently achieves the highest performance with
L= 2 across all federated settings. For the hidden dimension, when the number of clients is not large,
FedAux requires a relatively small hidden dimension, while with 20 clients, a hidden dimension of
256 yields the best results.
Impact of Similarity Temperature αIn Eq. (7), the similarity temperature parameter αis in-
troduced to modulate the sharpness of the similarity distribution. To evaluate the sensitivity of
FedAux to this hyperparameter, we test α∈ {0.1,1,10} across varying numbers of clients and
report the resulting accuracy in Fig. 8. The results show that while some configurations achieve
optimal accuracy at different values of α, for example, α= 0.1 is optimal for 20 clients on Cora and
α= 10 is optimal for 20 clients on Pubmed, directly setting α= 1 consistently provides satisfactory
performance across different datasets and client counts.
F Limitations and Future Work
The main limitation of our work is that while the kernel -based continuous aggregation scheme lets
each client learn a fully differentiable, data -driven ordering on the APV, it requires evaluating the
pairwise kernel for every node pair in the local client subgraph. Thus, the per -client computational
cost scales quadratically, O(N2
k), which is acceptable for small and medium subgraphs but can
dominate run -time on very large clients. Our future work focuses on addressing this scalability
bottleneck. One promising direction is to approximate the dense kernel with low -rank factorizations,
such as Nyström approximation, so that complexity scales linearly in Nkwith controllable error. We
stress that our core contribution is a privacy -preserving mechanism for personalized clustering clients
via theAPV, and reducing local computational load is a complementary line of future research.
31

---

*Source: 16556_Personalized_Subgraph_Fe.pdf — converted to markdown for benchmark reference (images omitted)*
