#!/usr/bin/env python3
"""prism test suite — zero external deps, runnable as `python3 tests/test_prism.py`.

Covers config/labels resolution, the three-piece binding (idempotency +
user-content protection), both MOC writers (in-table insertion), and the queue
parsers (YAML subset + folder scan). Exits non-zero on any failure so it can
gate CI.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "skills" / "prism" / "assets"
sys.path.insert(0, str(ASSETS))

import prism_config as pc          # noqa: E402
import prism_helpers as ph         # noqa: E402

_failures: list[str] = []
_passed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passed
    if cond:
        _passed += 1
        print(f"  ✓ {name}")
    else:
        _failures.append(f"{name} — {detail}")
        print(f"  ✗ {name} — {detail}")


# ---------------------------------------------------------------------------
def test_config_defaults():
    print("config / labels")
    cfg = pc.load_config(path="/nonexistent/none.json")
    check("defaults load with no file", cfg["lang"] == "en")
    check("path keys expanded", "~" not in cfg["vault_path"])
    L = pc.get_labels(cfg)
    check("EN labels", L["resources_heading"] == "## Resources")
    zh = pc.get_labels({**cfg, "lang": "zh"})
    check("ZH labels", zh["resources_heading"] == "## 资源")
    over = pc.get_labels({**cfg, "labels": {"resources_heading": "## Links"}})
    check("label override", over["resources_heading"] == "## Links")


def test_config_file(tmp):
    cfg_file = Path(tmp) / "config.json"
    cfg_file.write_text(json.dumps({"vault_path": "~/V", "lang": "zh", "parallel": 7}))
    cfg = pc.load_config(path=str(cfg_file))
    check("file merge: scalar", cfg["parallel"] == 7)
    check("file merge: keeps defaults", cfg["concept_budget"] == 8)
    check("file merge: lang", cfg["lang"] == "zh")
    check("file merge: expanduser", cfg["vault_path"].endswith("/V"))


# ---------------------------------------------------------------------------
def test_resources_block(tmp):
    print("inject_resources_block")
    cfg = pc.load_config(path="/nonexistent")  # EN defaults
    note = Path(tmp) / "Mamba.md"

    # create from scratch
    ph.inject_resources_block(str(note), "Mamba", arxiv_url="https://arxiv.org/abs/2312.00752",
                              github_url="https://github.com/state-spaces/mamba", cfg=cfg)
    c1 = note.read_text()
    check("stub created", note.exists())
    check("resources heading present", "## Resources" in c1)
    check("paper embed", "![[_slides/Mamba/Mamba.pdf]]" in c1)
    check("arxiv line", "2312.00752" in c1)

    # idempotent update on a hand-written note with user prose + custom heading
    note.write_text(
        "---\ntitle: x\n---\n\n# Paper Note: Mamba\n\n## Resources\n\n- old link\n\n"
        "## TL;DR\n\nUser-written summary that MUST survive.\n\n"
        "## My Notes\n\nprivate paragraph\n"
    )
    ph.inject_resources_block(str(note), "Mamba", arxiv_url="NEW", cfg=cfg)
    c2 = note.read_text()
    check("user prose survives", "User-written summary that MUST survive." in c2)
    check("private para survives", "private paragraph" in c2)
    check("resources refreshed", "NEW" in c2 and "old link" not in c2)

    # protection: a note that is ONLY a resources block must not be eaten
    only = Path(tmp) / "Only.md"
    only.write_text("# Paper Note: Only\n\n## Resources\n\n- a\n- b\n")
    before = only.read_text()
    ph.inject_resources_block(str(only), "Only", arxiv_url="Z", cfg=cfg)
    check("no-heading-after: untouched", only.read_text() == before)


# ---------------------------------------------------------------------------
def test_slides_moc(tmp):
    print("append_to_slides_moc")
    cfg = pc.load_config(path="/nonexistent")
    moc = Path(tmp) / "Slide Library.md"
    ph.append_to_slides_moc(str(moc), "Mamba", tag="SSM", venue="arXiv", year="2023",
                            slides_pdf_rel="x/Mamba.slides.pdf", cfg=cfg)
    ph.append_to_slides_moc(str(moc), "iCaRL", tag="CIL", venue="CVPR", year="2017",
                            slides_pdf_rel="x/iCaRL.slides.pdf", cfg=cfg)
    c = moc.read_text()
    check("two rows", c.count("| [[") == 2)
    # update in place, not duplicate
    ph.append_to_slides_moc(str(moc), "Mamba", tag="SSM-v2", venue="COLM", year="2024",
                            slides_pdf_rel="x/Mamba.slides.pdf", cfg=cfg)
    c2 = moc.read_text()
    check("update not duplicate", c2.count("[[Mamba]]") == 1)
    check("updated content", "SSM-v2" in c2)

    # insertion stays inside table even with trailing prose
    moc2 = Path(tmp) / "withprose.md"
    moc2.write_text("# Slide Library\n\n| Paper | Topic |\n|---|---|\n| [[A]] | x |\n\n## Notes\n- prose\n")
    ph.append_to_slides_moc(str(moc2), "B", tag="t", venue="v", year="2024",
                            slides_pdf_rel="p", cfg=cfg)
    lines = moc2.read_text().splitlines()
    b_idx = next(i for i, l in enumerate(lines) if "[[B]]" in l)
    notes_idx = next(i for i, l in enumerate(lines) if l.startswith("## Notes"))
    check("row inserted before prose", b_idx < notes_idx)


# ---------------------------------------------------------------------------
def test_project_moc(tmp):
    print("update_project_moc / bootstrap")
    cfg = pc.load_config(path="/nonexistent")
    # absent file -> returns False, does not create
    missing = Path(tmp) / "00 None.md"
    check("absent -> False", ph.update_project_moc(str(missing), "X") is False)
    check("absent -> not created", not missing.exists())

    moc = Path(tmp) / "00 Proj.md"
    moc.write_text(
        "# 00 Proj\n\n## Reading Queue\n\n"
        "| # | Paper | Method | Category | Venue · Year | Status | Priority | Relevance |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| 1 | [[Existing]] | E | cat | X 2020 | ✅ | ★★ | r |\n\n## Ideas\n- keep me\n"
    )
    ok = ph.update_project_moc(str(moc), "New", method_label="N", category="c2",
                               venue="ICLR", year="2024", status="✅", relevance="rel")
    c = moc.read_text()
    check("append returns True", ok is True)
    check("index auto-increment", "| 2 | [[New]]" in c)
    check("ideas section intact", "keep me" in c)
    # update existing keeps number
    ph.update_project_moc(str(moc), "Existing", method_label="E2", category="c", status="◐")
    c2 = moc.read_text()
    check("update keeps idx 1", "| 1 | [[Existing]]" in c2 and "E2" in c2)
    check("no dup of Existing", c2.count("[[Existing]]") == 1)


def test_bootstrap(tmp):
    cfg = pc.load_config(path="/nonexistent")
    cfg["vault_path"] = tmp
    cfg["notes_folder"] = "papers"
    path = ph.bootstrap_project("DemoProj", cfg=cfg)
    check("bootstrap creates moc", Path(path).exists())
    check("bootstrap has queue header", "| # |" in Path(path).read_text())
    # second call is a no-op (idempotent)
    Path(path).write_text(Path(path).read_text() + "\nEDITED\n")
    ph.bootstrap_project("DemoProj", cfg=cfg)
    check("bootstrap idempotent", "EDITED" in Path(path).read_text())


# ---------------------------------------------------------------------------
def test_queue(tmp):
    print("queue parsing")
    # folder scan
    d = Path(tmp) / "pdfs"; d.mkdir()
    (d / "gu2023mamba.pdf").write_bytes(b"%PDF")
    (d / "rebuffi2017icarl.pdf").write_bytes(b"%PDF")
    q = ph.folder_to_queue(str(d), project="P")
    check("folder scan count", len(q) == 2)
    check("folder scan ids", {x["id"] for x in q} == {"gu2023mamba", "rebuffi2017icarl"})

    # YAML (mini-parser fallback path)
    y = Path(tmp) / "q.yaml"
    y.write_text(
        "project: Demo\nparallel: 3\nnotes_strategy: full\n"
        "papers:\n"
        "  - id: mamba\n    path: " + str(d / "gu2023mamba.pdf") + "\n    method_name: Mamba\n"
        '  - id: new\n    arxiv: "2410.00001"\n'
    )
    parsed = ph.parse_paper_queue(str(y))
    check("yaml project", parsed["project"] == "Demo")
    check("yaml parallel int", parsed["parallel"] == 3)
    check("yaml papers", len(parsed["papers"]) == 2)
    check("yaml method override", parsed["papers"][0]["method_name"] == "Mamba")
    check("yaml arxiv source", parsed["papers"][1]["arxiv"] == "2410.00001")

    # unquoted arxiv (float in real YAML) must still come back as a clean string
    y2 = Path(tmp) / "q2.yaml"
    y2.write_text("papers:\n  - id: x\n    arxiv: 2312.00752\n")
    p2 = ph.parse_paper_queue(str(y2))
    check("unquoted arxiv coerced to str", isinstance(p2["papers"][0]["arxiv"], str))

    # validation: two sources -> error
    bad = Path(tmp) / "bad.yaml"
    bad.write_text("papers:\n  - id: x\n    path: /a.pdf\n    arxiv: 1\n")
    try:
        ph.parse_paper_queue(str(bad))
        check("multi-source rejected", False, "no error raised")
    except ValueError:
        check("multi-source rejected", True)


# ---------------------------------------------------------------------------
def test_arxiv_parse():
    print("arxiv figure parsing")
    html = (
        '<figure id="S1.F1"><img src="x1.png"><figcaption>Figure 1: '
        '<b>(Overview)</b> the thing.</figcaption></figure>'
        '<figure id="S3.F2"><img src="x3.png"><figcaption>Figure 2: results.</figcaption></figure>'
        '<figure id="noimg"><figcaption>no image here</figcaption></figure>'
    )
    figs = ph.parse_arxiv_figures(html)
    check("two figures parsed", len(figs) == 2)
    check("caption stripped of tags", figs[0]["caption"].startswith("Figure 1: (Overview) the thing"))
    check("src captured", figs[1]["src"] == "x3.png")


# ---------------------------------------------------------------------------
def test_state(tmp):
    print("checkpoint / resume")
    import prism_state as ps
    cfg = pc.load_config(path="/nonexistent")
    cfg["vault_path"] = tmp
    cfg["notes_folder"] = "papers"
    proj = "Demo"

    # fresh state
    st = ps.load_state(proj, cfg)
    check("fresh skeleton", st["papers"] == {})

    # update + persist + reload
    ps.update_paper(proj, "Mamba", cfg, status="in_progress", phase_done="analysis")
    ps.update_paper(proj, "Mamba", cfg, phase_done="figures")
    rec = ps.paper_status(proj, "Mamba", cfg)
    check("phase recorded", rec["phases"].get("analysis") and rec["phases"].get("figures"))
    check("status persisted", rec["status"] == "in_progress")
    check("atomic file exists", ps.state_path(proj, cfg).is_file())

    # mark done clears error
    ps.update_paper(proj, "Mamba", cfg, status="failed", error="boom")
    check("error set", ps.paper_status(proj, "Mamba", cfg)["error"] == "boom")
    ps.update_paper(proj, "Mamba", cfg, status="done")
    check("done clears error", ps.paper_status(proj, "Mamba", cfg)["error"] is None)

    # bad phase rejected
    try:
        ps.update_paper(proj, "X", cfg, phase_done="nonsense")
        check("bad phase rejected", False, "no error")
    except ValueError:
        check("bad phase rejected", True)

    # resume_plan from durable artifacts
    deck = Path(tmp) / "deck"
    deck.mkdir()
    plan0 = ps.resume_plan(str(deck), "Mamba")
    check("nothing done initially", not any(plan0.values()))
    check("resume_from = analysis", ps.next_phase(str(deck), "Mamba") == "analysis")

    c = ps.cache_dir(str(deck))
    (c / "Mamba_qa.md").write_text("qa")
    (c / "Mamba_note_body.md").write_text("body")
    (c / "Mamba_figmap.json").write_text("[]")
    plan1 = ps.resume_plan(str(deck), "Mamba")
    check("analysis now skippable", plan1["analysis"] is True)
    check("figures now skippable", plan1["figures"] is True)
    check("tables still pending", plan1["tables"] is False)
    check("resume_from = tables", ps.next_phase(str(deck), "Mamba") == "tables")

    # is_paper_done: needs a real-sized slides.pdf
    check("not done (no pdf)", ps.is_paper_done(str(deck), "Mamba") is False)
    (deck / "Mamba.slides.pdf").write_bytes(b"0" * (60 * 1024))
    (deck / "Mamba.slides.pptx").write_bytes(b"0")
    (deck / "Mamba.slides.md").write_text("deck")
    check("done with real pdf", ps.is_paper_done(str(deck), "Mamba") is True)
    check("render skippable", ps.resume_plan(str(deck), "Mamba")["render"] is True)

    # purge cache removes durable intermediates
    ps.purge_cache(str(deck))
    check("cache purged", not (deck / ".cache").exists())

    # corrupt state file -> skeleton, not crash
    ps.state_path(proj, cfg).write_text("{ not json")
    check("corrupt state recovers", ps.load_state(proj, cfg)["papers"] == {})


# ---------------------------------------------------------------------------
def test_refs(tmp):
    print("reference / .bib import")
    import prism_refs as pr

    # arXiv id extraction: new style (needs context), old style (anywhere), urls
    ids = pr.extract_arxiv_ids(
        "see arXiv:1409.0473 and arxiv.org/abs/2312.00752v2 and cs/0501001 "
        "(page 2017.1234 is NOT an id)")
    check("arxiv new w/ context", "1409.0473" in ids)
    check("arxiv url", "2312.00752v2" in ids)
    check("arxiv old style", "cs/0501001" in ids)
    check("bare number rejected", "2017.1234" not in ids)

    # DOIs
    check("doi extracted", pr.extract_dois("doi:10.1234/abc.def-5") == ["10.1234/abc.def-5"])

    # BibTeX parse — eprint, archivePrefix, url, nested braces in title
    bib = r"""
@article{bahdanau2014neural,
  title = {Neural Machine Translation by Jointly Learning to {Align} and Translate},
  author = {Bahdanau, Dzmitry and Cho, Kyunghyun and Bengio, Yoshua},
  journal = {arXiv preprint arXiv:1409.0473},
  year = {2014}
}
@inproceedings{vaswani2017attention,
  title = {Attention Is All You Need},
  author = {Vaswani, Ashish and others},
  archivePrefix = {arXiv},
  eprint = {1706.03762},
  year = {2017},
  doi = {10.5555/3295222.3295349}
}
@book{nobib, title = {No Identifier Here}, author = {Anon}, year = {2000}}
"""
    bf = Path(tmp) / "refs.bib"; bf.write_text(bib)
    ents = pr.parse_bib(bf.read_text() and str(bf))
    check("bib entry count", len(ents) == 3)
    by_key = {e["key"]: e for e in ents}
    check("bib arxiv from journal", by_key["bahdanau2014neural"]["arxiv"] == "1409.0473")
    check("bib arxiv from eprint", by_key["vaswani2017attention"]["arxiv"] == "1706.03762")
    check("bib nested-brace title clean",
          by_key["bahdanau2014neural"]["title"].endswith("Align and Translate")
          and "{" not in by_key["bahdanau2014neural"]["title"])
    check("bib doi", by_key["vaswani2017attention"]["doi"] == "10.5555/3295222.3295349")

    # refs_to_queue: arxiv → arxiv item, title-only → zotero item, none → dropped
    q = pr.refs_to_queue(ents, project="Demo")
    srcs = [("arxiv" in p) for p in q["papers"]]
    check("queue keeps 3 (2 arxiv + 1 title)", len(q["papers"]) == 3)
    check("title-only becomes zotero", any("zotero" in p for p in q["papers"]))
    # validate the produced queue actually parses through the queue validator
    qy = Path(tmp) / "refs_queue.yaml"
    lines = ["project: Demo", "parallel: 4", "papers:"]
    for p in q["papers"]:
        src = "arxiv" if "arxiv" in p else "zotero"
        val = p.get("arxiv") or p.get("zotero")
        lines += [f"  - id: {p['id']}", f'    {src}: "{val}"']
    qy.write_text("\n".join(lines) + "\n")
    parsed = ph.parse_paper_queue(str(qy))
    check("generated queue re-parses", len(parsed["papers"]) == 3)

    # PDF-style reference text parsing (numbered list with arxiv ids)
    reftext = (
        "References\n"
        "[1] J. Ba, J. Kiros, G. Hinton. Layer normalization. arXiv:1607.06450, 2016.\n"
        "[2] D. Bahdanau et al. Neural machine translation. arXiv:1409.0473, 2015.\n"
        "[3] Some book with no identifier at all, Publisher, 2010.\n"
    )
    pents = pr.parse_references_from_text(reftext)
    got_ids = {e["arxiv"] for e in pents if e["arxiv"]}
    check("pdf-refs find arxiv ids", {"1607.06450", "1409.0473"} <= got_ids)
    # title heuristic: prose clause beats the author name-list
    e1 = next(e for e in pents if e["arxiv"] == "1607.06450")
    check("pdf-refs title is prose not authors",
          "layer normalization" in e1["title"].lower() and "Kiros" not in e1["title"])


# ---------------------------------------------------------------------------
def test_discovery(tmp):
    print("discovery source → queue")
    import prism_refs as pr
    # heterogeneous recommender records: varied field names, arxiv in id/url
    raw = {
        "papers": [
            {"arxiv_id": "2312.00752", "title": "Mamba", "score": 9.5, "tldr": "selective SSM"},
            {"id": "2106.09685", "name": "LoRA", "rating": 7.0, "reason": "PEFT staple"},
            {"url": "https://arxiv.org/abs/1706.03762", "title": "Transformer", "score": 6.0},
            {"title": "Some venue-only paper", "doi": "10.1/x", "score": 3.0},
            {"junk": "no usable fields"},
        ]
    }
    f = Path(tmp) / "digest.json"
    f.write_text(json.dumps(raw))
    items = pr.load_discovery(str(f))
    check("discovery normalized count", len(items) == 4)  # junk dropped
    by_t = {i["title"]: i for i in items}
    check("arxiv from arxiv_id", by_t["Mamba"]["arxiv"] == "2312.00752")
    check("arxiv from id field", by_t["LoRA"]["arxiv"] == "2106.09685")
    check("arxiv from url", by_t["Transformer"]["arxiv"] == "1706.03762")
    check("score parsed float", by_t["Mamba"]["score"] == 9.5)
    check("why from tldr alias", by_t["Mamba"]["why"] == "selective SSM")

    q = pr.discovery_to_queue(items, project="Daily", top_k=3)
    check("queue project", q["project"] == "Daily")
    check("top_k applied", len(q["papers"]) == 3)
    check("sorted by score desc", q["papers"][0]["title"] == "Mamba")
    check("score→priority P1 for top", q["papers"][0]["priority"] == "P1")
    check("why→relevance", q["papers"][0]["relevance"] == "selective SSM")
    check("title-only→zotero", any("zotero" in p for p in
          pr.discovery_to_queue(items)["papers"]))

    # min_score filter
    q2 = pr.discovery_to_queue(items, min_score=7.0)
    check("min_score filter", len(q2["papers"]) == 2)

    # the generated queue must pass the real queue validator
    qy = Path(tmp) / "disc_queue.yaml"
    lines = ["project: Daily", "papers:"]
    for p in q["papers"]:
        src = "arxiv" if "arxiv" in p else "zotero"
        lines += [f"  - id: {p['id']}", f'    {src}: "{p.get("arxiv") or p.get("zotero")}"']
    qy.write_text("\n".join(lines) + "\n")
    check("discovery queue re-parses", len(ph.parse_paper_queue(str(qy))["papers"]) == 3)


# ---------------------------------------------------------------------------
def main():
    with tempfile.TemporaryDirectory() as tmp:
        test_config_defaults()
        Path(tmp + "/cfg").mkdir(exist_ok=True)
        test_config_file(tmp + "/cfg")
        test_resources_block(tmp)
        test_slides_moc(tmp)
        test_project_moc(tmp)
        test_bootstrap(tmp)
        test_queue(tmp)
        test_arxiv_parse()
        test_state(tmp)
        test_refs(tmp)
        test_discovery(tmp)

    print()
    if _failures:
        print(f"FAILED {len(_failures)} / {_passed + len(_failures)}")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print(f"OK — {_passed} checks passed")


if __name__ == "__main__":
    main()
