---
marp: true
theme: default
paginate: true
math: mathjax
size: 16:9
header: '{Method} · {Venue} {Year}'
footer: 'prism · Twelve Questions + every figure & table'
style: |
  section {
    font-family: 'PingFang SC', 'Helvetica Neue', sans-serif;
    font-size: 21px;
    padding: 38px 52px;
  }
  section h1 { font-size: 34px; color: #1a365d; margin-bottom: 10px; }
  section h2 { font-size: 26px; color: #2c5282; border-bottom: 2px solid #bee3f8; padding-bottom: 5px; margin-bottom: 12px; }
  section h3 { font-size: 21px; color: #2d3748; }
  section.title h1 { font-size: 44px; text-align: center; margin-top: 50px; }
  section.title h3 { font-size: 22px; text-align: center; color: #4a5568; font-weight: normal; }
  section.section-divider { background: #2c5282; color: white; }
  section.section-divider h1 { color: #f6e05e; text-align: center; margin-top: 180px; font-size: 56px; }
  section.section-divider h3 { color: #cbd5e0; text-align: center; font-weight: normal; }
  section.insight { background: #fffaf0; }
  section.insight h2 { color: #c05621; border-color: #fbd38d; }
  section.takeaway { background: #1a365d; color: white; }
  section.takeaway h1, section.takeaway h2 { color: #f6e05e; }
  .star { color: #d69e2e; }
  .small { font-size: 16px; color: #718096; }
  .tag { background: #edf2f7; padding: 2px 8px; border-radius: 4px; font-size: 17px; margin-right: 4px; }
  .figkey { background: #e6fffa; padding: 10px 14px; border-left: 4px solid #38b2ac; margin-top: 8px; font-size: 19px; }
  blockquote { border-left: 4px solid #4299e1; padding-left: 14px; color: #2d3748; margin: 8px 0; }
  code { background: #edf2f7; padding: 2px 6px; border-radius: 4px; }
  table { font-size: 17px; }
  img { display: block; margin: 0 auto; }
---

<!-- ============================================================ -->
<!--  Usage notes (delete this block when done)                   -->
<!--  - Every main-text Figure / Table gets its own page, each     -->
<!--    with a .figkey read-key box                                -->
<!--  - Use <!-- _class: section-divider --> for section breaks    -->
<!--  - Use <!-- _class: insight --> to highlight Q3               -->
<!--  - Use <!-- _class: takeaway --> for the Q12 finale           -->
<!--  - Formulas use $...$ / $$...$$; break long lines short       -->
<!--  - Image paths are relative to this .md: assets/{method}_fig_*.png -->
<!-- ============================================================ -->

<!-- _class: title -->

# {Paper Title}

### {Author1, Author2, ...}
### {Venue} {Year}

<span class="tag">{tag1}</span> <span class="tag">{tag2}</span> <span class="tag">{tag3}</span>

`{arxiv_url}` · `{code_url}`

---

## TL;DR · one card

> {2-3 sentence elevator summary: core idea + cost + effect}

| | |
|---|---|
| **Problem** | {scenario + data/model + pain point} |
| **Core idea** | {1-sentence insight} |
| **Cost** | {what this paper pays for that insight} |
| **Effect** | {key numbers} |
| **Follow-up** | ★★★ / ★★ / ★ |

---

<!-- _class: section-divider -->

# 1.  Problem & Gap

### Q1 · Q2

---

## Q1 · What problem does it solve

**Scenario**: {...}
**Pain points**:
- {...}
- {...}
**Goal**: {...}
**Why now is the right time to do this**: {...}

---

## Q2 · Where prior methods fall short (Gap)

| Category | Representative | Flaw | How this paper attacks it |
|----------|----------------|------|---------------------------|
| {Method A} | {paper/system} | {flaw} | {this paper's response} |
| {Method B} | {paper/system} | {flaw} | {this paper's response} |
| {Method C} | {paper/system} | {flaw} | {this paper's response} |

> **Key diagnosis**: {one sentence capturing the essence of the gap}

---

<!-- _class: section-divider -->

# 2.  Core Insight ⭐

### Q3

---

<!-- _class: insight -->

## Q3 · Core idea

> **{1-2 sentence intuition: the key regularity the authors exploit is XXX}**

**Why it was not possible before**:
- {the underlying mechanistic limitation}

**How this paper solves it**:
- {what concrete math/algorithm change it lands as}

**Cost**: {what side effect this insight introduces}

---

<!-- _class: insight -->

## Q3 · Why this insight works

| Capability | Intuition | How it is realized |
|------------|-----------|--------------------|
| {capability 1} | {...} | {...} |
| {capability 2} | {...} | {...} |
| {capability 3} | {...} | {...} |

**Theoretical depth**: {is there a Theorem / correspondence with existing theory}

---

<!-- _class: section-divider -->

# 3.  Architecture & Algorithm

### Q4 · Q5 · every architecture figure in the paper

---

## Figure {N} · {figure topic}

![w:840](assets/{method}_fig_xK.png)

<div class="figkey">

**Read-key**: {1-3 sentences on what this figure says; point out the meaning of the labels, colors, and arrows.}

</div>

**Levels of understanding**:
- **Static structure** — {...}
- **Dynamic behavior** — {...}
- **Design motive** — {...}

---

<!-- Copy the previous page's structure — one page per architecture Figure -->

## Figure {N+1} · {next figure}

![w:880](assets/{method}_fig_xK.png)

<div class="figkey">

**Read-key**: {...}

</div>

**Design philosophy** / **evolution path**: {...}

---

## Q4 · Pipeline (text version)

```
Input: {X}
   ↓
Module 1: {Name}  →  {role}
   ↓
Module 2: {Name}  →  {role}
   ↓
...
   ↓
Output: {Y}
```

---

## Algorithm 1 → Algorithm 2 comparison (if applicable)

| | **Algorithm 1 (baseline)** | **Algorithm 2 (this paper)** |
|---|---|---|
| Parameter X | {...} | {...} |
| Parameter Y | {...} | {...} |
| Computation | {...} | {...} |

> **The one fundamental difference**: {...}
> **Side effect**: {why engineering optimization is needed to make it practical}

---

## Q5 · Role of each module

| Module | What it does | What breaks without it |
|--------|--------------|------------------------|
| {Module A} | {...} | {ablation consequence} |
| {Module B} | {...} | {ablation consequence} |
| {Module C} | {...} | {ablation consequence} |

---

<!-- _class: section-divider -->

# 4.  Math

### Q6 · formula triplets

---

## Q6 · Formula 1/N · {topic}

$$
{core formula}
$$

**Meaning**: {...}

**Symbols**:
- {symbol} — {meaning}
- {symbol} — {meaning}

**Intuition**: {plain-language description of what this formula is doing}

---

<!-- Copy the previous page's structure -->

## Q6 · Formula 2/N · {topic}

$$
{second formula}
$$

**Meaning**: {...}

---

<!-- _class: section-divider -->

# 5.  Experimental Setup

### Q7, first half

---

## Q7 · Datasets

| Modality | Dataset | Scale | Use |
|----------|---------|-------|-----|
| {modality} | {name} | {scale} | {use} |

## Baselines

- {baseline 1}: {characteristics}
- {baseline 2}: {characteristics}
- {baseline 3}: {characteristics}

---

## Q7 · Metrics + training details

**Metrics**

| Task | Metric |
|------|--------|
| {task} | {metric} |

**Training / implementation**
- **Backbone**: {...}
- **Optimization**: {lr / scheduler / optimizer}
- **Training length**: {epochs / steps / tokens}
- **Compute**: {GPU model × count}
- **Code**: {open-sourced or not + URL}

---

<!-- _class: section-divider -->

# 6.  Results

### One page per figure / table · each with a read-key box

---

## Table {N} · {table topic}

<!-- 🚨 Tables must be screenshots of the original PDF — never re-drawn as markdown -->
<!-- See the "Iron rule · tables are screenshots" section in SKILL.md for the screenshot workflow -->

![w:820](assets/{method}_table_K.png)

<div class="figkey">

**Read-key**: {what this table demonstrates; what conclusions the row-wise and column-wise comparisons support}

</div>

---

## Figure {N} · {figure topic}

![w:820](assets/{method}_fig_xK.png)

<div class="figkey">

**Experimental setup**: {axes / objects compared / key variables}

</div>

**Read-key**:
- {observation 1}
- {observation 2}

**What this figure argues**: {which claim the authors use it to support}

---

<!-- Repeat the format above for each main-text Figure / Table — **every one needs a page**, none may be skipped -->

---

<!-- _class: section-divider -->

# 7.  Ablation & Source of Gains

### Q8

---

## Q8 · Where the gains come from

| Source | Contribution | Magnitude | Evidence |
|--------|--------------|-----------|----------|
| {source A} ⭐ | {primary / secondary / no gain} | {number} | {Table / Figure} |
| {source B} | {...} | {number} | {...} |
| {source C} | {...} | {number} | {...} |

> Main gain comes from **{X}**; secondary from **{Y}**; **{Z}** is the engineering safeguard.

---

## Q8 · One-sentence attribution

> **The accuracy gain ≈ X% from A, Y% from B.**
> **The efficiency gain ≈ 100% from C.**

The two contributions are orthogonal / coupled: {explanation}

---

<!-- _class: section-divider -->

# 8.  Limits · Transfer · Improve

### Q9 · Q10 · Q11

---

## Q9 · Limitations (honest list)

1. **{limitation 1}** — {fails under this specific scenario}
2. **{limitation 2}** — {compute / data / assumption constraint}
3. **{limitation 3}** — **【inferred】** {not stated in the paper but inferred}
4. **{limitation 4}**
5. **{limitation 5}**

---

## Q10 · Can it transfer

| Direction | Existing work | How to do it |
|-----------|---------------|--------------|
| {direction 1} | {paper} | {change} |
| {direction 2} | {paper} | {change} |
| {direction 3} | — | {self-consistent change} |

> This paper is not a replacement for X; it is the best solution in the {Y quadrant}.

---

## Q11 · Improvement ideas (3 creative ones)

**💡 {idea 1}**
- {what to do}
- Benefit: {...}; risk: {...}

**💡 {idea 2}**
- {what to do}
- Benefit: {...}; risk: {...}

**💡 {idea 3}**
- {what to do}
- Benefit: {...}; risk: {...}

---

<!-- _class: takeaway -->

## Q12 · Take-away

> {2-3 sentence spoken-introduction version}

<br>

| Dimension | Rating |
|-----------|--------|
| **Insight real or not** | {real / incremental} |
| **Engineering value** | ★★★ / ★★ / ★ |
| **Worth following up** | ★★★ / ★★ / ★ |
| **Recommendation** | {read closely / skim / cite / reproduce / skip} |

---

## Related Work

**Prior**
- **{prior 1}** — {one-liner}
- **{prior 2}** — {one-liner}

**Follow-up**
- **{follow-up 1}** — {one-liner}
- **{follow-up 2}** — {one-liner}

---

<!-- _class: title -->

# Thank you

### `prism` · Twelve Questions + every figure & table
### {total pages} pages

### Want the full Obsidian note? Say "give me the full note"
### Want a deep dive on a section? Say "analyze Section X"
