# The twelve-question framework

This is the method paper-prism is built on, written for a human reader. You can use it
without paper-prism at all — it is just a disciplined way to read a paper so that you
can re-explain it afterward, unaided.

The core idea is one sentence: **the goal is not to summarize a paper, it is to
be able to teach it.** A summary leaves you with "I read something about this." A
good twelve-question pass leaves you able to stand at a whiteboard and walk a
colleague through the paper's problem, its key idea, why its math looks the way
it does, where its numbers come from, and where it breaks — without the PDF open.

Two habits make that work, and they run through every question below:

- **Each answer carries a self-check** — a one-line statement of how you'd *know*
  you actually understood, not just that you wrote something down. Treat the
  self-check as the pass/fail test for your answer.
- **Mark what the paper doesn't say.** When you're inferring rather than quoting,
  flag it **【inferred】**; when the information simply isn't there, say so. Honest
  gaps beat confident fabrication.

Output convention: lead with a 2–3 sentence elevator summary (that's Q12, pulled
to the front so a reader can triage fast), then answer Q1–Q12 in order.

---

## The twelve questions

### Q1 — What problem does the paper solve?

One sentence: **in what setting, using what data/model, does it fix what concrete
pain?** All three parts matter — a problem statement without the setting is too
vague to be useful.

*Good answer:* names the scenario, the object being worked on, and the specific
pain — not "improves performance," but "*makes state-space sequence models match
Transformer quality while keeping linear-time inference, which prior SSMs
couldn't because their dynamics were input-independent.*"

*Self-check:* I can state, in one sentence, what setting this paper is about and
what problem it solves.

### Q2 — Where do prior methods fall short? (the gap)

One to three concrete shortcomings, each with a **named subject** — which *class*
of method, or which representative paper, falls short, and how. "Existing methods
are limited" is not an answer; "*method family A can't do X because Y*" is.

*Self-check:* I can answer "if this paper didn't exist, what specific problems
would the old methods still hit?"

### Q3 — What is the core insight? ⭐

One or two sentences of **intuition** — the regularity, structure, or assumption
the authors exploited to make the method work. This is the most-abused question,
so it has its own worked example below. The rule: **not a list of modules.**

*Self-check:* when I state the insight, I can explain *why performance improves
because of it* — not just recite the names of the components.

### Q4 — What is the method pipeline?

The end-to-end flow as `input → module 1 → module 2 → … → output`. If it's
complex, split into preprocessing / backbone / loss-and-training.

*Self-check:* without the paper, I could draw the pipeline with its main modules
and explain it to someone.

### Q5 — What does each module do?

Module by module: **name + what it does + why it's needed / whether it could be
replaced.** For each key module, add the one line that proves you understand it —
*what breaks if you remove it.*

*Self-check:* for any module, I can say why it is designed that way and what its
role is in the whole.

### Q6 — What are the equations doing?

Pick the 2–5 load-bearing formulas (the objective, the key transform, the
important constraint). For each: what the input/output variables are, its
physical or statistical meaning, and its role in the method (training target?
regularizer? feature transform?).

*Good answer:* explains each equation in plain language — "*this term penalizes
the model when the gate stays open on irrelevant tokens*" — rather than reading
the symbols aloud.

*Self-check:* I can explain in plain words roughly what each key formula is
doing, without naming symbols.

### Q7 — How is it validated?

Datasets (name + brief characteristic), baselines compared against, metrics (OA /
mIoU / FID / …), and whether there are ablations and qualitative visualizations.

*Self-check:* I can judge whether this experimental design is actually enough to
support the paper's main claims.

### Q8 — Where do the gains come from?

Read the result tables *and the ablations together* and attribute the improvement:
architecture? training tricks (lr schedule, augmentation, a new loss)? data
handling? or just more compute / a bigger model? Be both **quantitative and
qualitative** — "*+Z points on dataset Y over baseline X, mostly from adding
module A.*"

*Self-check:* I can point to *which part of the design matters most*, instead of
vaguely crediting "the overall improvement."

### Q9 — What are the limitations?

At least two. Narrow datasets, strong scene assumptions, high compute/memory
cost, hyperparameter sensitivity, only small-scale validation, and so on.
Whatever the paper doesn't admit, infer it reasonably and mark it **【inferred】**.

*Self-check:* I can answer "in what situations might this method not apply, or
need to be used with care?"

### Q10 — Is it transferable?

One to three *coherent* extensions: to other tasks (classification → detection),
other modalities (image → video, unimodal → multimodal), or other frameworks
(dropping the idea into a Transformer stack).

*Self-check:* I can give at least one concrete idea for reusing this paper's
approach somewhere else.

### Q11 — How would you improve it? (your ideas)

Two or three improvement ideas, building on everything above: change the
structure (swap a block, add MoE / RL / …), change the training (new loss,
regularizer, sampling), or change the application (few-shot, online, cross-domain).
Each with its **upside and its risk.**

*Self-check:* I can propose a few *reasoned* directions, not just "tune the
hyperparameters more."

### Q12 — Can you explain it in 2–3 sentences?

The spoken-intro version: **what problem + core method + what result**, in two or
three sentences you could actually say out loud. (Put this at the *front* of your
write-up for fast triage.)

*Self-check:* from just these 2–3 sentences, I can roughly recall the whole
paper's key points.

---

## Worked micro-example: Q3 done wrong vs. right

Take a state-space sequence model (Mamba-style) as the example. Here is the
difference the Q3 rule is pointing at.

**❌ Module-list answer (what to avoid):**

> "The core idea is a selective SSM block, plus a hardware-aware parallel scan,
> plus a gated MLP, combined into a simplified architecture."

This is fluent and even accurate — but it is the *table of contents of the
architecture*, not the insight. It names *what was built* and tells you nothing
about *why it works*. You could memorize it and still be unable to explain why
the model is any good. It fails the self-check: it cannot answer "why does
performance improve?"

**✅ Insight answer (what to aim for):**

> "Earlier linear-time SSMs were forced to use the *same* dynamics for every
> input token, so they couldn't choose what to remember and what to forget —
> that's why they lost to attention on content-dependent tasks. The insight is
> to make the SSM parameters *functions of the input*, giving the model an
> attention-like ability to select information, while keeping a scan formulation
> that still runs in linear time."

This names the regularity the authors exploited (selectivity is what SSMs were
missing relative to attention), explains *why the change helps* (content-dependent
gating recovers the capability attention had), and connects it back to the
problem from Q1 (linear time without sacrificing quality). The modules from the
wrong answer are now *consequences* of this insight, not a substitute for it. It
passes the self-check: it explains why performance improves.

The litmus test for any Q3 answer: **strip out every proper noun and module name.
If nothing explanatory is left, you wrote a module list, not an insight.**

---

## Using it at scale (the condensed pass)

For a single paper, answer all twelve. When you're working through many papers at
once, doing the full twelve on each is too slow — but skipping the analysis
entirely defeats the purpose. The compromise is a **condensed five-question
pass**: **Q1 (problem) + Q3 (insight) + Q4-brief (pipeline) + Q9 (limitations) +
Q12 (elevator)**, one or two sentences each. These five are the load-bearing
ones — what it does, why it works, how, where it breaks, and the one-line recap —
and you can expand any paper to the full twelve on demand. The condensed pass is
the *floor*, not an excuse to skip thinking; it's the minimum that still lets a
later, fuller note be trustworthy.

---

## A note on style

Lead with motivation and intuition, then go to formula details. Analogies and
small examples are welcome as long as they don't sacrifice rigor. Mark every
uncertain point **【inferred】** or "information insufficient." Keep each answer
tight — a few sentences, not a wall of text; the discipline of brevity forces you
to actually distill rather than dump.
