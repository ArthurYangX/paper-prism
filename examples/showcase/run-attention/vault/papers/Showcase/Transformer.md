---
title: "Attention Is All You Need"
method_name: "Transformer"
authors: [Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Łukasz Kaiser, Illia Polosukhin]
year: 2017
venue: "NeurIPS (NIPS) 2017"
tags: [transformer, self-attention, sequence-transduction, machine-translation, attention]
project: Showcase
arxiv_id: "1706.03762"
arxiv_url: https://arxiv.org/abs/1706.03762
code_url: https://github.com/tensorflow/tensor2tensor
image_source: local
created: 2026-06-03
---

# Paper Note: Attention Is All You Need

<!-- paper-prism:resources:start -->
## Resources

- 📄 Paper: ![[Transformer.pdf]]
- 🎬 Slides: ![[Transformer.slides.pdf]]
- 🌐 arXiv: https://arxiv.org/abs/1706.03762
- 💻 Code: https://github.com/tensorflow/tensor2tensor
- 📁 Project: [[00 Showcase]]
<!-- paper-prism:resources:end -->

> The links above live in this **## Resources** block; paper-prism refreshes them in place on each run. Keep paper background below.

| Field | Value |
|-------|-------|
| Affiliations | Google Brain · Google Research · University of Toronto |
| Date | June 2017 |
| Project page | — |
| Baseline | [[GNMT]] · [[ConvS2S]] · [[ByteNet]] |

---

## TL;DR

> A [[sequence transduction]] model built **entirely from [[attention]]**, with no recurrence and no convolution. By letting every position attend directly to every other, it makes the path between any two tokens $O(1)$ and the whole layer fully parallel — training to a new WMT'14 EN-DE / EN-FR state of the art (28.4 / 41.8 BLEU) at a small fraction of prior training cost.

---

## Key Contributions

1. **The [[Transformer]] — the first transduction model based solely on attention**: replaces the recurrent (or convolutional) encoder–decoder with stacked [[self-attention]] + position-wise feed-forward layers, removing sequential computation along the sequence dimension.
2. **[[Multi-Head Attention]] + [[Scaled Dot-Product Attention]]**: a cheap dot-product attention scaled by $1/\sqrt{d_k}$, run in $h$ parallel "heads" so the model can jointly attend to information from different representation subspaces.
3. **State of the art at a fraction of the cost**: 28.4 BLEU on WMT'14 EN-DE (>2 BLEU over the previous best, including ensembles) and 41.8 BLEU on EN-FR (single-model SOTA), trained in 3.5 days on 8 GPUs — 1–2 orders of magnitude less training compute than the strongest baselines.
4. **Generality**: the same architecture, essentially unchanged, reaches strong results on English constituency parsing, evidence that "attention is all you need" beyond translation.

---

## Background

### Problem
[[Sequence transduction]] tasks such as machine translation were dominated by recurrent encoder–decoder networks ([[RNN]]/[[LSTM]]/[[GRU]]), usually augmented with an [[attention]] mechanism. The goal of this paper is a transduction architecture that keeps attention's modeling power but **removes the recurrence**, so training can parallelize and long-range dependencies become easy to model.

### Prior Gap
- **Recurrent models** ([[seq2seq]], [[GNMT]]): the hidden state $h_t$ is a function of $h_{t-1}$, so computation is **inherently sequential** along the sequence — it cannot parallelize within a training example, and memory limits batching across long sequences. Relating two distant positions takes $O(n)$ steps.
- **Convolutional models** ([[ConvS2S]], [[ByteNet]], Extended Neural GPU): reduce sequential computation, but the number of operations to relate two arbitrary positions still **grows with distance** — linearly for ConvS2S, logarithmically for ByteNet — making distant dependencies harder to learn.
- **Self-attention existed** in reading comprehension, summarization, and entailment work, but **no transduction model relied on self-attention alone** (no RNN/CNN) for its representations.

### Motivation
If a single layer lets each position attend to all positions at once, the maximum path length between any two tokens collapses to a constant, and the layer is fully parallel. The price — losing order information and diluting the resolution of a single weighted average — can be paid back cheaply by **positional encodings** and **multiple attention heads**. See [[Self-Attention]] and the [[Transformer]] core insight.

---

## Method

### Architecture
The [[Transformer]] keeps the standard **encoder–decoder** shape, but every recurrent layer is replaced by attention + a feed-forward network:
- **Input**: token [[embeddings]] (scaled by $\sqrt{d_{\text{model}}}$) **plus** a [[Positional Encoding]].
- **Encoder**: a stack of $N=6$ identical layers, each = [[Multi-Head Attention|multi-head self-attention]] + [[Position-wise Feed-Forward Network]], each sub-layer wrapped in a [[Residual Connection]] and [[Layer Normalization]] ($\text{LayerNorm}(x + \text{Sublayer}(x))$, all sub-layers output dimension $d_{\text{model}}=512$).
- **Decoder**: a stack of $N=6$ identical layers, each adding a third sub-layer — [[Encoder-Decoder Attention]] over the encoder output — and **masking** its self-attention so position $i$ can only attend to positions $\le i$.
- **Output**: a linear projection + softmax over the vocabulary (weight-tied with the embeddings).

### Core Modules

#### Module 1: [[Scaled Dot-Product Attention]]
**Design motive**: a similarity-weighted lookup that is far cheaper than additive attention (it is just matrix multiplication), while staying stable at large $d_k$.
**How it works**: compute dot products of the query with all keys, divide each by $\sqrt{d_k}$, softmax to get weights, and take the weighted sum of the values. The $1/\sqrt{d_k}$ scale counteracts the growth of dot-product magnitude with dimension.
**What breaks without it**: without the scaling, for large $d_k$ the dot products grow large in magnitude, pushing the softmax into regions with vanishingly small gradients — training becomes unstable / slow.

#### Module 2: [[Multi-Head Attention]]
**Design motive**: a single attention average blurs together everything it attends to; the authors want the model to attend to **different positions in different representation subspaces** simultaneously.
**How it works**: linearly project $Q,K,V$ into $h=8$ lower-dimensional subspaces ($d_k=d_v=d_{\text{model}}/h=64$), run scaled dot-product attention in each head in parallel, concatenate, and project back. Total cost is similar to single-head attention at full dimension.
**What breaks without it**: with one head, the ablation shows quality drops (single-head is 0.9 BLEU below the best setting) — the model loses the ability to track several distinct relations (e.g. syntactic vs. positional) at once.

#### Module 3: [[Position-wise Feed-Forward Network]]
**Design motive**: attention is linear in its values; the model needs per-position non-linearity and capacity.
**How it works**: the same two-layer MLP with a [[ReLU]] in between ($d_{ff}=2048$) is applied independently and identically to every position.
**What breaks without it**: the model loses most of its non-linear transformation capacity; attention alone cannot represent the needed feature interactions.

#### Module 4: [[Positional Encoding]]
**Design motive**: self-attention is **permutation-invariant** — it has no notion of order — so position must be injected explicitly.
**How it works**: add fixed sinusoidal signals of geometrically increasing wavelength to the input embeddings; each dimension is a sinusoid, letting the model attend by relative offsets (for any fixed $k$, $PE_{pos+k}$ is a linear function of $PE_{pos}$). The ablation shows learned positional embeddings perform essentially identically; sinusoids are chosen for possible extrapolation to longer sequences.
**What breaks without it**: the model cannot distinguish word order — "dog bites man" and "man bites dog" become indistinguishable to the encoder.

#### Module 5: Masked decoder [[self-attention]]
**Design motive**: preserve auto-regressive generation — output position $i$ must not see future positions.
**How it works**: set the pre-softmax scores for illegal (future) connections to $-\infty$, so they receive zero attention weight.
**What breaks without it**: information about future tokens leaks back, breaking the train/inference consistency of left-to-right decoding.

#### Module 6: [[Residual Connection]] + [[Layer Normalization]]
**Design motive**: train a deep (6+6 layer) stack stably.
**How it works**: every sub-layer output is $\text{LayerNorm}(x + \text{Sublayer}(x))$; residuals also require all sub-layers and embeddings to share dimension $d_{\text{model}}$.
**What breaks without it**: deep stacks suffer from poor gradient flow and unstable optimization.

---

## Key Formulas

### Formula 1: [[Scaled Dot-Product Attention|attention]]

$$
\text{Attention}(Q, K, V) = \text{softmax}\!\left(\frac{QK^{\top}}{\sqrt{d_k}}\right) V
$$

**Meaning**: each query retrieves a convex combination of the value vectors, weighted by query–key similarity.

**Symbols**:
- $Q \in \mathbb{R}^{n \times d_k}$ — queries (one row per position)
- $K \in \mathbb{R}^{m \times d_k}$, $V \in \mathbb{R}^{m \times d_v}$ — keys and values
- $d_k$ — key/query dimension; $\sqrt{d_k}$ is the stabilizing temperature

**Intuition**: "soft dictionary lookup" — match a query against every key, then average the values by how well they matched, divided by $\sqrt{d_k}$ so the softmax does not saturate.

### Formula 2: [[Multi-Head Attention]]

$$
\text{MultiHead}(Q,K,V) = \text{Concat}(\text{head}_1, \dots, \text{head}_h)\,W^{O}
$$

$$
\text{where}\quad \text{head}_i = \text{Attention}(Q W_i^{Q},\, K W_i^{K},\, V W_i^{V})
$$

**Meaning**: run $h$ attentions in parallel subspaces and merge them.

**Symbols**:
- $W_i^{Q}, W_i^{K} \in \mathbb{R}^{d_{\text{model}} \times d_k}$, $W_i^{V} \in \mathbb{R}^{d_{\text{model}} \times d_v}$ — per-head projections
- $W^{O} \in \mathbb{R}^{hd_v \times d_{\text{model}}}$ — output projection
- $h = 8$, $d_k = d_v = 64$

**Intuition**: eight "views" of the sequence, each free to specialize (one head may track the previous token, another a syntactic head), recombined into one representation.

### Formula 3: [[Position-wise Feed-Forward Network]]

$$
\text{FFN}(x) = \max(0,\, x W_1 + b_1)\, W_2 + b_2
$$

**Meaning**: an identical two-layer ReLU MLP applied to each position separately.

**Symbols**:
- $W_1 \in \mathbb{R}^{512 \times 2048}$, $W_2 \in \mathbb{R}^{2048 \times 512}$ — expand then project back
- inner dimension $d_{ff} = 2048$

**Intuition**: between attention "mixing" steps, give each token its own non-linear transform.

### Formula 4: [[Positional Encoding]]

$$
PE_{(pos,\, 2i)} = \sin\!\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right), \qquad
PE_{(pos,\, 2i+1)} = \cos\!\left(\frac{pos}{10000^{2i/d_{\text{model}}}}\right)
$$

**Meaning**: encode absolute position as a bank of sinusoids of geometrically spaced frequencies.

**Symbols**:
- $pos$ — position index; $i$ — dimension index
- wavelengths form a geometric progression from $2\pi$ to $10000 \cdot 2\pi$

**Intuition**: a "binary-clock"-like multi-frequency code; because $PE_{pos+k}$ is a fixed linear function of $PE_{pos}$, the model can learn to attend by **relative** offset.

### Formula 5: [[Learning-rate warmup schedule]]

$$
lrate = d_{\text{model}}^{-0.5} \cdot \min\!\left(step^{-0.5},\; step \cdot warmup^{-1.5}\right)
$$

**Meaning**: linearly warm the learning rate up for `warmup` steps, then decay it as the inverse square root of the step number.

**Symbols**:
- $warmup = 4000$ steps; $d_{\text{model}} = 512$

**Intuition**: ramp up gently while the model is fragile, then anneal — important for training such a deep attention stack with [[Adam]].

---

## Key Figures & Tables

> All figures/tables are screenshots of the original PDF (paper-prism's iron rule — tables are never re-typed as markdown). Read-keys explain; they do not restate the numbers.

### Figure 1: The Transformer — model architecture

![[Transformer_fig_1.png|360]]

**Read-key**: the encoder (left) and decoder (right) are each a stack of $N\times$ identical layers. In every layer the curved arrows are [[Residual Connection|residual]] bypasses feeding "Add & Norm"; the encoder layer has multi-head self-attention + feed-forward, while the decoder layer inserts a middle [[Encoder-Decoder Attention]] block and uses a **Masked** Multi-Head Attention at the bottom. Position is injected by adding [[Positional Encoding]] to the input/output [[embeddings]] at the very bottom.

### Figure 2: Scaled Dot-Product & Multi-Head Attention

![[Transformer_fig_2.png|620]]

**Read-key**: left is the operator chain of one attention — MatMul($QK^\top$) → Scale → optional Mask → SoftMax → MatMul(with $V$). Right shows multi-head: $Q,K,V$ are each linearly projected $h$ times, attention runs in parallel per head, and the outputs are concatenated and projected. The "$h$" annotation marks the stacked parallel heads.

### Figure 3: Attention follows long-distance dependencies

![[Transformer_fig_3.png|680]]

**Read-key**: an encoder self-attention head in layer 5 connects the verb "making" to its distant complement "more difficult" — a long-range dependency captured in a **single** attention step (the $O(1)$ path of Table 1). Different colors are different heads; line opacity is attention weight.

### Table 1: Per-layer complexity, sequential ops, and path length

![[Transformer_table_1.png|720]]

**Read-key**: the quantitative justification for the whole design — self-attention pays a higher per-layer cost but reduces both the number of **sequential operations** and the **maximum path length** between positions to constants, whereas a recurrent layer's path length grows with sequence length. Shorter paths make long-range dependencies easier to learn.

### Table 2: Main translation results (WMT'14 BLEU + training cost)

![[Transformer_table_2.png|720]]

**Read-key**: the headline result. The big Transformer is the top row on both metrics while sitting in the lowest training-cost bracket; the paper's argument is "better quality **and** far less compute," not a quality-for-cost trade. Note the bottom two rows are the paper's own models — every other row is a genuine baseline or baseline ensemble.

### Table 3: Variations on the Transformer (ablations)

![[Transformer_table_3.png|720]]

**Read-key**: rows (A)–(E) vary one factor from the `base` row. The takeaways: attention heads have a sweet spot (too few **or** too many hurt); shrinking the key dimension $d_k$ hurts; bigger models help; dropout and label smoothing both help; and **learned positional embeddings (row E) match the sinusoids** almost exactly.

### Table 4: English constituency parsing (generalization)

![[Transformer_table_4.png|720]]

**Read-key**: a Transformer trained for parsing — with little task-specific tuning — is competitive with strong, parsing-specific models in both the WSJ-only and semi-supervised settings, supporting the claim that the architecture transfers beyond translation.

---

## Experiments

### Datasets

| Dataset | Scale | Tokenization | Use |
|---------|-------|--------------|-----|
| WMT 2014 English–German | ~4.5M sentence pairs | 37,000 shared [[Byte-Pair Encoding\|BPE]] tokens | train / test (newstest2014) |
| WMT 2014 English–French | ~36M sentences | 32,000 word-piece vocabulary | train / test (newstest2014) |
| WSJ Penn Treebank (parsing) | ~40K sentences (WSJ-only) + ~17M (semi-supervised) | — | constituency parsing transfer |

### Implementation Details
- **Backbone**: [[Transformer]] — base ($d_{\text{model}}=512$, $d_{ff}=2048$, $h=8$, $N=6$, 65M params) and big ($d_{\text{model}}=1024$, $d_{ff}=4096$, $h=16$, $N=6$, 213M params).
- **Optimizer**: [[Adam]] ($\beta_1=0.9$, $\beta_2=0.98$, $\epsilon=10^{-9}$) with the warmup schedule (Formula 5), $warmup=4000$.
- **Regularization**: residual [[Dropout]] $P_{drop}=0.1$ (0.3 for big EN-DE) + [[Label Smoothing]] $\epsilon_{ls}=0.1$.
- **Hardware / schedule**: 8× NVIDIA P100. Base ≈ 0.4 s/step × 100K steps (~12 h); big ≈ 1.0 s/step × 300K steps (~3.5 days).
- **Decoding**: [[Beam Search]] (beam 4, length penalty 0.6) with checkpoint averaging.

### Qualitative Results
Inspecting individual attention heads (Figures 3–5) shows heads that specialize: some follow long-distance syntactic dependencies, some resolve anaphora (e.g. what "its" refers to), and many appear to learn interpretable structural roles — qualitative evidence that multi-head self-attention captures linguistically meaningful relations.

---

## Critique

### Strengths
1. **Parallelism + short dependency paths**: removing recurrence makes every layer parallel and the inter-token path $O(1)$ — the root cause of both the speed and the quality gains (Table 1 → Table 2).
2. **State of the art at low cost**: a rare "Pareto win" — higher BLEU *and* 1–2 orders of magnitude less training compute than the strongest baselines.
3. **Simplicity & generality**: a small set of reusable primitives (attention, FFN, residual, LayerNorm) that transfer cleanly to parsing — and, historically, far beyond.
4. **Interpretability**: attention maps give a window into what the model relates.

### Limitations
1. **Quadratic cost in sequence length**: self-attention is $O(n^2 \cdot d)$ per layer (stated in Table 1). For very long sequences this is expensive; the paper proposes *restricted* (neighborhood-$r$) self-attention as a remedy but **does not evaluate it at scale**.
2. **Scope of evaluation**: only translation (two language pairs) and one parsing task. Other modalities (image/audio/video) are named only as **future work**.
3. **Fixed positional encoding & length extrapolation**: sinusoids are *hypothesized* to extrapolate to longer sequences than seen in training, but this is **not empirically verified** 【inferred】.
4. **Inference is still sequential**: decoding remains auto-regressive (one token at a time), so the $O(1)$-path advantage applies to training, not generation latency 【inferred】.
5. **Cost of the best model**: the big model (213M params, 3.5 days on 8 P100) is still substantial; the "cheap" comparison is relative to even more expensive baselines.

### Improvements
1. **Restricted / local attention** to break the $O(n^2)$ wall for long inputs (the paper itself flags this).
2. **Less-sequential generation** — non-autoregressive or partially parallel decoding (named as future work).
3. **Relative / learned positional schemes** — row (E) shows learned positions are no worse, leaving room to explore relative-position encodings.

### Reproducibility
- [x] Code open-sourced ([tensor2tensor](https://github.com/tensorflow/tensor2tensor))
- [x] Complete training details (optimizer, schedule, regularization, hardware all reported)
- [x] Datasets public (WMT'14)
- [x] Hyperparameters for both base and big given (Table 3)

---

## Related Work

### Builds on
- [[attention]] (Bahdanau et al.): content-based alignment for translation — generalized here to self-attention.
- [[seq2seq]] / [[GNMT]]: the encoder–decoder framing the Transformer keeps.
- [[ConvS2S]] / [[ByteNet]] / Extended Neural GPU: prior attempts to cut sequential computation with convolutions.
- [[Layer Normalization]], [[Residual Connection]], [[Label Smoothing]]: training ingredients reused.

### Compared with
- [[GNMT]] + RL, [[ConvS2S]], [[ByteNet]], [[MoE]], Deep-Att + PosUnk: the WMT'14 baselines in Table 2.

### Method-related
- [[Self-Attention]]: the core primitive.
- [[Multi-Head Attention]] / [[Scaled Dot-Product Attention]]: the key components.

### Follow-up (historical)
- [[BERT]], [[GPT]], [[Vision Transformer|ViT]]: the model families this architecture launched.

---

## Quick Reference

> [!summary] Attention Is All You Need (Transformer)
> - **Core**: a transduction model built entirely from attention — no recurrence, no convolution.
> - **Method**: stacked multi-head self-attention + position-wise FFN, with positional encodings, in an encoder–decoder.
> - **Results**: 28.4 BLEU EN-DE / 41.8 BLEU EN-FR on WMT'14 — SOTA at a fraction of the training cost.
> - **Code**: https://github.com/tensorflow/tensor2tensor

---

## Twelve-Question Cheat-Sheet

| # | Question | Answer |
|---|----------|--------|
| Q1 | What problem does it solve? | Sequence transduction (e.g. MT) without recurrence — so training parallelizes and long-range dependencies are easy to model. |
| Q2 | Where do prior methods fall short (gap)? | RNNs are inherently sequential ($O(n)$ path, no intra-example parallelism); CNN models (ConvS2S/ByteNet) still need distance-growing ops to relate positions. |
| Q3 | Core insight (the regularity exploited)? | Let every position attend to every other directly: the inter-token path becomes $O(1)$ and the layer is fully parallel; pay back lost order/resolution with positional encodings + multiple heads. |
| Q4 | Architecture / pipeline? | embed + positional encoding → 6× encoder (self-attn + FFN) → 6× decoder (masked self-attn + enc-dec attn + FFN) → linear + softmax. |
| Q5 | Role of each module? | scaled dot-product attn (cheap, stable lookup); multi-head (parallel subspaces); FFN (per-position non-linearity); positional encoding (inject order); masking (autoregression); residual+LayerNorm (deep stability). |
| Q6 | Key formulas? | Attention softmax$(QK^\top/\sqrt{d_k})V$; MultiHead concat of heads; FFN ReLU-MLP; sinusoidal PE; lrate warmup-then-inverse-sqrt. |
| Q7 | Experimental setup? | WMT'14 EN-DE (4.5M, 37K BPE) & EN-FR (36M, 32K wp); baselines GNMT/ConvS2S/ByteNet/MoE; BLEU + training FLOPs; ablations in Table 3; parsing transfer in Table 4. |
| Q8 | Where do the gains come from? | Quality: big model 28.4/41.8 BLEU > all prior single & ensemble (Table 2). Efficiency: full parallelism, 1–2 orders less compute. Ablations: head count, model size, dropout, label smoothing all matter (Table 3). |
| Q9 | Limitations? | $O(n^2)$ in sequence length; only MT+parsing evaluated; sinusoid extrapolation unverified 【inferred】; inference still sequential 【inferred】. |
| Q10 | Can it transfer? | Yes — strong on constituency parsing with little tuning (Table 4); historically generalized to nearly all of deep learning. |
| Q11 | Improvement ideas? | Restricted/local attention for long inputs; non-autoregressive decoding; relative-position encodings. |
| Q12 | Take-away (worth following up)? | Foundational. The first all-attention transduction model; SOTA translation at low cost; the architecture that launched the Transformer era. ★★★ |

---

*Note created: 2026-06-03 · paper-prism showcase (public paper).*
