# prism design notes

The rationale behind the choices that make prism different from "paste a PDF and
ask for a summary." Each section is honest about *why* — including the costs.
If you disagree with a decision, this is where the argument is.

---

## Why twelve questions with self-checks

The design target is not a summary. It is **unaided re-explanation**: after
prism is done, you should be able to put the paper down and explain it to a
colleague — its problem, its core idea, why its math is shaped that way, where
its numbers come from, where it breaks — without looking back. A summary
optimizes for "I read something about this." The twelve questions optimize for
"I could teach this."

That shift is enforced by two mechanisms. First, every one of the twelve answers
ships with a **"how I'd know I understood it" self-check** — a single line
stating the bar the answer must clear. Q4's self-check, for instance, is "without
the paper I could draw the pipeline with its main modules and explain it to
someone." The self-check is not decoration; it is the acceptance test for the
answer, and it is what stops the model from producing fluent prose that doesn't
actually demonstrate comprehension.

Second, the questions are written to resist the specific ways LLM summaries cheat.
The sharpest example is the **Q3 insight-not-module-list rule**. Asked for a
paper's core idea, a model will happily list "we add a gating block, a selective
scan, and a hardware-aware kernel" — which is the *architecture*, not the
*insight*. prism forbids this: Q3 must be one or two sentences of intuition
naming the regularity, structure, or assumption the authors exploited to make
the method work, such that you can explain *why performance improves*, not just
recite component names. (See the worked micro-example in
`docs/twelve-questions.md`.) Paired with this is the honesty discipline: anything
the paper does not actually state is marked **【inferred】** (or "information
insufficient" when even inference isn't supported), and the analyst reads
intro + method + experiments + conclusion rather than paraphrasing the abstract.

The cost of this framework is real: twelve questions with self-checks is slower
and more tokens than "TL;DR this." prism's answer is the batch *condensed*
mode — Q1 + Q3 + Q4-brief + Q9 + Q12, the five load-bearing questions — which
scales to a hundred papers while still refusing to skip the analysis step
entirely. The condensed pass is the floor, not an off switch.

---

## The table-screenshot iron rule

Re-typing a paper's tables into markdown is, in our experience, the single most
common bug in AI-generated paper notes — so prism makes it a hard rule: **every
table from the paper is embedded as a screenshot of the original; it is never
re-drawn as a markdown `| ... |`.**

The reasons stack up, and each one alone would be enough:

- **It corrupts the data.** Re-typing a results table is a transcription task
  over dozens of numbers, and transcription has an error rate. Bold (the
  best-in-column marker), underlines (second-best), up/down arrows (higher- or
  lower-is-better), ± standard deviations, and merged header cells all routinely
  get dropped or mangled in the markdown round-trip. A note whose numbers are
  subtly wrong is worse than no note.
- **It discards the authors' visual language.** A table's layout — what is
  grouped, what is bolded, which baselines are adjacent — is a deliberate
  argument the authors are making. Flattening it into a generic markdown grid
  throws that argument away.
- **It reads as "an AI reworded it."** A screenshot of the real table signals "I
  read this paper." A retyped grid signals the opposite. For notes meant to be
  trusted and shared, that signal matters.

The SOP is mechanical and lives in `prism_helpers.py`: render the relevant pages
with `render_pdf_pages()` (which shells out to `pdftoppm` at 200 DPI, ~1700×2200
for A4/Letter), Read each page PNG to find the table's pixel bounding box, then
`crop_region()` (PIL) cuts it out — header rows and caption included. As
calibration: a single-column table is roughly 520–800 px wide, a cross-column
one roughly 1500 px. The one sanctioned exception is a trivial 2×3 table, which
may stay markdown; **main-result and ablation tables must be screenshots, no
exceptions.** Note also that Agent A (analysis) is explicitly forbidden from
typing the paper's tables — it leaves a `<!-- TABLE_N_PLACEHOLDER -->` for the
table agent's screenshot — so the rule holds even inside the parallel fan-out.

The honest cost: screenshots are heavier than text, don't reflow, and aren't
searchable or copy-pasteable. prism takes that trade because a faithful,
uneditable table beats a lightweight, lossy one every time for a study artifact.

---

## Plan-C three-piece binding

"Plan C" is the output layout: for each paper, **the note, the original PDF, and
the slide deck live together in one folder**, plus two global indexes — a slide
Library MOC and a per-project reading queue.

```
{vault}/{notes_folder}/{project}/
├── {method}.md                         the note (Obsidian entry point)
└── _slides/{method}/
    ├── {method}.pdf                     original paper, copied in
    ├── {method}.slides.md / .pdf / .pptx
    └── assets/  {method}_fig_*.png  {method}_table_*.png
{vault}/_MOC/Slide Library.md            global deck index
{vault}/.../{project}/00 {project}.md    project reading queue
```

Why co-location beats scattered markdown:

- **One paper is one self-contained unit.** Everything you need to study it — the
  source, the deep note, the deck, the cropped figures and tables — is in a
  single folder. Move it, archive it, or share it and nothing dangles.
- **It is Obsidian-native, and survives vault moves.** Embeds use relative
  `![[...]]` links, so the note shows the PDF and the deck inline at the top
  (injected by `inject_resources_block`), and the whole package keeps working if
  the vault is relocated. There are no absolute paths to break.
- **The two MOCs give you the views co-location can't.** Per-folder layout is
  great for one paper but useless for "show me every deck" or "what's my reading
  queue for this project." `append_to_slides_moc` maintains a global, preview-rich
  deck index; `update_project_moc` (bootstrapped by `bootstrap_project`)
  maintains a per-project queue with status/priority/relevance columns. You get
  both the local package *and* the global views.
- **Re-runs protect hand-written notes.** This is the subtle, important one. The
  binders are idempotent and surgical: `inject_resources_block` refreshes *only*
  the resources block — it replaces from the heading up to the next `#`/`##` and
  bails if there isn't one — so if you have been hand-editing a note's prose,
  re-running prism updates the links at the top and **never touches your
  writing** (unless you explicitly say "rewrite"). The MOC functions match the
  paper's existing row by `[[method_name]]` and edit in place. Process a paper
  twice and you get one row and one resources block, not duplicates.

The cost: this is more machinery than dropping a single `.md` in a folder, and
it assumes Obsidian (or at least `[[wikilink]]` + `![[embed]]` semantics). prism
accepts that coupling because the payoff — a navigable, self-healing, re-runnable
knowledge base instead of a pile of orphan files — is the entire point of the
tool. Mode B ("local" / "next to the PDF") exists as the escape hatch when you
*don't* want vault integration: it writes the deck next to the source PDF with no
copy, no note binding, and no MOC updates.

---

## Concept budget + alias dedup

prism wraps each technical term in `[[concept]]` at first mention, which builds a
concept graph across your library. Done naively, this explodes. A single paper
easily mentions twenty linkable terms; a hundred papers is then on the order of
**100 × 20 = 2000 wikilinks**, most pointing at notes that were never created —
a graph that is mostly broken edges, which is worse than no graph because it
looks navigable and isn't.

Two rules keep it sane. First, a **concept budget**: at most `cfg.concept_budget`
(default **8**) *new* concept notes per paper. Beyond the budget, extra terms are
downgraded to bold and listed under "Concepts not yet created" rather than
minting more dangling links — so each paper contributes a small number of
*real*, fleshed-out concept notes instead of a swarm of stubs. Second, **alias
dedup**: before creating a concept, prism checks whether it already exists under
a different name, so `Mamba` / `Mamba SSM` / `Selective SSM` collapse to one note
with aliases instead of becoming three competing files that fragment the graph.

The cost is that the graph is intentionally *sparse* — not every term you might
want to click is linked. prism bets that a smaller graph of solid nodes is far
more useful than a dense graph of broken ones, especially at the scale where the
tool earns its keep. The budget and dedup rules live in
`references/concept-categories.md`.

---

## Method-name extraction

Batched papers usually arrive as `firstauthor+year+keyword.pdf` —
`gu2023mamba.pdf`, `de2021continual.pdf`. The trap that catches essentially every
tool is treating `keyword` as the method name. Often it isn't: `continual`,
`multimodal`, `selfsupervised` are *topic* words, not method names. Name a note
`Continual.md` and you've mislabeled the paper and poisoned every link to it.

prism resolves identity with a **four-tier confidence ladder**, acting only on
evidence as strong as the action:

1. **High — use directly.** A Zotero title of the form `XXX: ...`, an abstract
   that says "We propose XXX" / "Our model, XXX", or a title prefix before the
   colon (`Mamba: Linear-Time...` → `Mamba`).
2. **Medium — use, but report it.** A GitHub repo name (`state-spaces/mamba` →
   `Mamba`), or an all-caps acronym repeated five or more times.
3. **Low — ask the user.** The filename keyword is a generic topic word; or it's
   a survey / benchmark / dataset paper with no single "method"; or the name is
   Greek/formula-shaped (π₀.₅).
4. **Fallback — `{Author}{Year}`**, saved to the inbox folder with
   `needs_review: true` in frontmatter, so nothing is silently mis-named.

Names are normalized to ASCII (internal caps and hyphens are fine — `HyperKD`,
`ViT-S`; no spaces, CJK, or Greek), and a collision with an existing note of a
*different* `arxiv_id` triggers a `{method}-{year}.md` rename plus a cross-link.
The ladder is deliberately conservative: prism would rather ask once, or fall
back to an honest `AuthorYear` stub flagged for review, than confidently invent
a wrong method name — because a wrong name is the kind of error that quietly
corrupts an entire library's graph.

---

## i18n by labels

prism separates *what it says* from *what language it says it in*. All generated
headings — the resources block, the TL;DR and contributions headings, the MOC
column titles — come from a label set in `prism_config.py`, switchable between
`"en"` and `"zh"` via a single `lang` config key (with per-label overrides under
`labels`). Set `lang: "zh"` and the output note's headings render in Chinese;
set `"en"` and they render in English. The body content follows the user's
language, but the *structure* is driven entirely by labels, so adding a third
language is a matter of adding a preset, not editing the pipeline. `get_labels()`
resolves the active set; the helper functions that write files all accept an
optional `cfg` and look their headings up rather than hard-coding strings — which
is also what lets a single codebase produce either experience without forking.

**Triggers, by contrast, stay bilingual** regardless of output language. The
phrases that *invoke* prism — "read paper" and "读一下", "make a deck" and
"出 PPT" — are matched in both English and Chinese at all times, because a user
fluently code-switches between the two even when they want output in just one.
The asymmetry is intentional: output language is a *preference* (pick one),
recognition is *robustness* (accept both). Conflating them — only recognizing
triggers in the configured output language — would make the tool fail to fire
exactly when a bilingual user reaches for it in their other language.
