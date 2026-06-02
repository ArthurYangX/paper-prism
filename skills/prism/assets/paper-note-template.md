---
title: "{Title}"
method_name: "{MethodName}"
authors: [{Authors}]
year: {Year}
venue: {Venue}
tags: [{tags}]
zotero_collection: {zotero_path}
image_source: online  # online (default) / mixed / local
arxiv_html: {arxiv_html_url}  # if available
created: {date}
---

# Paper Note: {Title}

## Resources

- 📄 Paper: ![[{MethodName}/{MethodName}.pdf]]
- 🎬 Slides: ![[{MethodName}/{MethodName}.slides.pdf]]
- 🌐 arXiv: {arxiv_url}
- 💻 Code: {code_url}
- 📁 Project: [[00 {project}]]
- 📚 Index: [[{index_note}]]

> The links above (PDF / Slides / arXiv / Code / Project / Index) live in this **## Resources** block.
> Keep only paper background below to avoid duplication.

| Field | Value |
|-------|-------|
| Affiliations | {Affiliations} |
| Date | {Month Year} |
| Project page | {project_page_url} |
| Baseline | [[{baseline_paper}]] |

---

## TL;DR

> {One sentence capturing the paper's core contribution, under 50 words.}

---

## Key Contributions

1. **{Contribution 1 title}**: {brief explanation}
2. **{Contribution 2 title}**: {brief explanation}
3. **{Contribution 3 title}**: {brief explanation}

---

## Background

### Problem
{What problem does this paper set out to solve?}

### Prior Gap
{Where do existing methods fall short?}

### Motivation
{Why do the authors believe their approach solves it?}

---

## Method

### Architecture

<!-- Wrap every technical term in [[concept]] inline links -->

{MethodName} adopts a **{architecture type}** architecture:
- **Input**: language instruction $l$ + observation $o_t$ + state $s_t$
- **Backbone**: {backbone network used}
- **Core module**: [[{core technique 1}]] for [[{core technique 2}]]
- **Output**: [[Action Chunking|action chunk]] $a_{t:t+k}$
- **Total parameters**: {parameter count}

### Core Modules

#### Module 1: {name}

**Design motive**: leverage [[{related concept}]] to achieve {goal}.

**How it works**:
- Use [[{technique A}]] for {step 1}
- Apply [[{technique B}]] to realize {step 2}

**What breaks without it**: {what fails / degrades if this module is removed}

#### Module 2: {name}

{Same format — motive + how it works + what breaks without it. Keep inline concept links.}

---

## Key Formulas

<!-- Each formula is a triplet: name [[concept|label]], the $$LaTeX$$, its meaning, and a symbol table -->
<!-- Use [[concept|label]] in the heading to link back to the concept library -->

### Formula 1: [[{concept name}|{formula purpose}]]

$$
{formula content}
$$

**Meaning**: {one sentence on what this formula does}

**Symbols**:
- $\tau \sim \mathcal{U}(0, 1)$: {meaning}
- ${symbol 2}$: {meaning}

### Formula 2: [[{concept name}]] loss

$$
\mathcal{L}_{total} = \lambda_1 \mathcal{L}_{task} + \lambda_2 \mathcal{L}_{reg}
$$

**Meaning**: {overall role of the loss function}

**Symbols**:
- $\lambda_1, \lambda_2$: weighting coefficients
- $\mathcal{L}_{task}$: {role of the task loss}
- $\mathcal{L}_{reg}$: {role of the regularization term}

### Formula 3: sampling / inference

$$
{inference formula}
$$

**Meaning**: {explanation of the inference procedure}

{... list every important formula in the paper ...}

---

## Key Figures & Tables

<!-- Figures and tables are emitted as placeholders, then filled in by the coordinator from /tmp/{method}_figmap.json and /tmp/{method}_tablemap.json. -->
<!-- Do NOT re-type a paper table as markdown and do NOT replace a figure with prose. Tables are screenshots of the original PDF, never markdown. -->

### Figure 1: {title}

<!-- FIGURE_1_PLACEHOLDER -->

**Read-key**: {1-3 sentences on what this figure says; point out the meaning of labels, colors, and arrows.}

### Figure 2: {title}

<!-- FIGURE_2_PLACEHOLDER -->

**Read-key**: {1-3 sentences; the key design point this figure illustrates.}

### Table 1: {title}

<!-- TABLE_1_PLACEHOLDER -->

**Read-key**: {1-3 sentences on the key finding; do NOT restate the numbers.}

### Table 2: {title}

<!-- TABLE_2_PLACEHOLDER -->

**Read-key**: {1-3 sentences on the most important conclusion, e.g. from the ablation.}

{... list every important figure and table in the paper, each as a placeholder + read-key ...}

---

## Experiments

### Datasets

| Dataset | Scale | Characteristics | Use |
|---------|-------|-----------------|-----|
| {Dataset1} | {size} | {characteristics} | train / test |
| {Dataset2} | {size} | {characteristics} | test |

### Implementation Details

- **Backbone**: {backbone network used}
- **Optimizer**: {Adam/SGD, learning rate}
- **Batch size**: {size}
- **Training epochs**: {epochs}
- **Hardware**: {GPU model and count}

### Qualitative Results

{Key observations from the qualitative results.}

---

## Critique

### Strengths
1. {strength 1}
2. {strength 2}
3. {strength 3}

### Limitations
1. {limitation 1}
2. {limitation 2}

### Improvements
1. {improvement direction 1}
2. {improvement direction 2}

### Reproducibility
- [ ] Code open-sourced
- [ ] Pretrained models
- [ ] Complete training details
- [ ] Dataset available

---

## Related Work

### Builds on
- [[{prior work 1}]]: {note}
- [[{prior work 2}]]: {note}

### Compared with
- [[{compared method 1}]]: {why compared}
- [[{compared method 2}]]: {why compared}

### Method-related
- [[{core technique 1}]]: core method
- [[{core technique 2}]]: key component

### Hardware / data-related
- [[{hardware or dataset}]]: {note}

---

## Quick Reference

> [!summary] {Paper Title}
> - **Core**: {one-sentence core}
> - **Method**: {key method}
> - **Results**: {main results}
> - **Code**: {GitHub link}

---

## Twelve-Question Cheat-Sheet

| # | Question | Answer |
|---|----------|--------|
| Q1 | What problem does it solve? | {answer} |
| Q2 | Where do prior methods fall short (gap)? | {answer} |
| Q3 | Core insight (the regularity exploited)? | {answer} |
| Q4 | Architecture / pipeline? | {answer} |
| Q5 | Role of each module? | {answer} |
| Q6 | Key formulas? | {answer} |
| Q7 | Experimental setup (data / baselines / metrics)? | {answer} |
| Q8 | Where do the gains come from? | {answer} |
| Q9 | Limitations? | {answer} |
| Q10 | Can it transfer to other settings? | {answer} |
| Q11 | Improvement ideas? | {answer} |
| Q12 | Take-away (worth following up)? | {answer} |

---

*Note created: {timestamp}*
