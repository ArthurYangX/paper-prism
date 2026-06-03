# Detailed Note Quality Standards

## Number & table fidelity (the #1 validated failure mode)

> Lesson (adversarial validation): the single most damaging error class is
> **fabricating or mislabeling numbers from multi-row results tables** — e.g.
> inventing an SNLI baseline score that appears nowhere in the paper, or citing
> the proposed method's own row under a baseline's name.

Rules whenever a number enters Q7/Q8 or the note's experiment section:

1. **Cell-level provenance.** Before writing any number, locate its exact
   `(table, row label, column)`. If you can't, don't write it.
2. **Never invent a baseline number.** If the paper doesn't report a value a
   comparison needs, write "not reported" — never a plausible-looking fill.
3. **Baseline rows must actually be baselines.** Results tables interleave the
   paper's own method and its variants with baselines. Re-read a row's label
   before calling it "the X baseline"; do not dress up the proposed method's own
   row as a baseline.
4. **Cross-table superlatives by delta-from-baseline.** "Best X" across separate
   ablation tables (each varying from a shared baseline) is ranked by delta from
   that baseline, not by raw value; name the compared row in any "X vs Y" claim.
5. **Don't strengthen the source's claim** when paraphrasing ("highly correlated"
   ≠ "common"; "not too correlated" ≠ "orthogonal"); keep the hedge or mark
   【inferred】.
6. **Flag source-internal discrepancies** (body vs caption vs table) as
   【paper-internal discrepancy】 rather than silently picking one.

Checklist:
- [ ] Every number in the note traces to a specific table cell.
- [ ] Every "baseline" cited is a real baseline row, not the method's own variant.
- [ ] No invented numbers; missing values say "not reported".
- [ ] Cross-table "best" claims use delta-from-baseline.

## Formula quality checks

> Lesson (the DreamerV1 incident): a formula must not only "be present" but also "be correct".

### 5 classes of formula errors that must be checked

| # | Error type | Example | How to check |
|---|------------|---------|--------------|
| 1 | **Variable collision** | $v(s_\tau) = \sum_\tau r_\tau$ ($\tau$ is both a free variable and the summation variable) | Ensure the bound variable and the free variable do not share a name |
| 2 | **Formula–text mismatch** | Text says "stop-gradient" but the formula has no $\operatorname{sg}(\cdot)$ | Properties stated in the text must be reflected in the formula |
| 3 | **Inconsistent notation** | Body text uses $p$ for the posterior, the formula uses $q$ | Use the original paper's notation consistently throughout |
| 4 | **Wrong sub/superscript or summation range** | $\sum_{n=1}^{H}$ written as $\sum_{n=1}^{H-1}$ | Verify character by character against the original paper |
| 5 | **Missing key operator** | Omitting $\mathbb{E}$, $\nabla$, stop-gradient, etc. | Confirm all operators are complete |

### Obsidian MathJax compatibility

1. **Avoid overly long single-line formulas** (split into an `aligned` block when >80 characters)
2. **`$$` blocks must have a blank line before and after** (otherwise they will not render)
3. Safe commands: `\operatorname{}`, `\text{}`, `\begin{aligned}`, `\underbrace{}`
4. `\Big`, `\bigg` are preferable to `\left`/`\right` for handling nested braces

### Formula self-check checklist

- [ ] Variable names consistent with the context? No collisions?
- [ ] Mathematical properties described in text reflected in the formula?
- [ ] Summation / integration ranges consistent with the original paper?
- [ ] Long formulas split?
- [ ] Blank lines before and after `$$`?

## Table extraction standards — screenshots, never markdown 🚨

**Every table is a SCREENSHOT of the original PDF — never re-typed as markdown.**
Re-typing corrupts numbers, bold (the best-in-column marker), underlines, arrows,
± std-devs, and merged cells, and it reads as "an AI reworded it" rather than "I
read the paper". This is paper-prism's iron rule (see SKILL.md § Iron rule and
`docs/design-notes.md`).

SOP — the table agent does this; do **NOT** hand-write a markdown table:

```bash
# 1. render the page(s) holding the table at 200 DPI
python3 skills/paper-prism/assets/prism_helpers.py render paper.pdf /tmp {first} {last} {method}_page
# 2. Read the page PNG, find the table's pixel box, crop it (header rows + caption included):
PYTHONPATH=skills/paper-prism/assets python3 -c "from prism_helpers import crop_region; \
  crop_region('/tmp/{method}_page-NN.png', 'assets/{method}_table_K.png', (left, top, right, bottom))"
# 3. Read the crop back: caption + header + ALL data rows present, no truncation. Re-crop if off.
```

Embed it in the note as `![[{method}_table_K.png]]`. The only sanctioned exception
is a trivial 2×3 table you author as your **own** synthesis (e.g. a module-role
table) — a paper's result/ablation tables are **always** screenshots.

## Figure extraction standards

**Every paper note must include all figures** — not a single one may be missed.

Also check the **project homepage** for additional figures (e.g. pretraining pipeline diagrams, ablation visualizations, etc.).

Each figure must include:
1. **Title** — `### Figure X: English title / native-language title`
2. **Image** — external links preferred (arXiv HTML, project homepage, etc.); fall back to local only when none can be found
3. **Caption** — explain the figure's content and key information

## Extraction completeness self-check checklist

**Zero-omission principle: all figures, all formulas, all tables must appear in the note.**

Figures:
- [ ] How many figures does the paper have? Are they all included in the note?
- [ ] Does each external-link URL correspond to the correct figure?
- [ ] Have those without external links been downloaded locally to `assets/` and embedded with `![[]]`?
- [ ] Does the project homepage have extra figures? Have they been added?

Formulas:
- [ ] How many formulas does the paper have? Are they all included in the note?
- [ ] Variable names consistent? No collisions?
- [ ] Long formulas split for Obsidian compatibility?

Tables:
- [ ] How many tables does the paper have? Are they all included in the note, with all rows complete?
