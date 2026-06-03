#!/usr/bin/env python3
"""paper-prism test suite — zero external deps, runnable as `python3 tests/test_prism.py`.

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

ASSETS = Path(__file__).resolve().parents[1] / "skills" / "paper-prism" / "assets"
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

    # a note that is ONLY a (legacy) resources block: refresh it safely (no crash,
    # new url present, sentinels added) — there is no prose to lose.
    only = Path(tmp) / "Only.md"
    only.write_text("# Paper Note: Only\n\n## Resources\n\n- a\n- b\n")
    ph.inject_resources_block(str(only), "Only", arxiv_url="ZURL", cfg=cfg)
    oc = only.read_text()
    check("only-resources note refreshed", "ZURL" in oc and "paper-prism:resources:start" in oc)

    # 🔴 #1 REGRESSION: a metadata table BELOW the resources links must survive
    # a re-bind (this is the data-loss bug the review caught).
    tbl = Path(tmp) / "WithTable.md"
    tbl.write_text(
        "---\ntitle: x\n---\n\n# Paper Note: WithTable\n\n"
        "## Resources\n\n- old paper\n- old slides\n\n"
        "> keep this blockquote\n\n"
        "| Field | Value |\n|---|---|\n| Affiliations | MIT |\n| Date | 2024 |\n\n"
        "---\n\n## TL;DR\n\nuser summary\n"
    )
    ph.inject_resources_block(str(tbl), "WithTable", arxiv_url="https://first.example", cfg=cfg)
    ph.inject_resources_block(str(tbl), "WithTable", arxiv_url="https://second.example", cfg=cfg)  # 2nd bind
    c2 = tbl.read_text()
    check("#1 metadata table survives re-bind", "| Affiliations | MIT |" in c2 and "| Date | 2024 |" in c2)
    check("#1 blockquote survives", "> keep this blockquote" in c2)
    check("#1 user TL;DR survives", "user summary" in c2)
    check("#1 resources actually refreshed", "second.example" in c2 and "first.example" not in c2)
    check("#1 idempotent shape (sentinels, single block)", c2.count("paper-prism:resources:start") == 1)

    # 🟠 #2 REGRESSION: an h3 directly under Resources must still refresh
    h3 = Path(tmp) / "H3.md"
    h3.write_text("# Paper Note: H3\n\n## Resources\n\n- a\n\n### Subsection\n\nbody\n")
    ph.inject_resources_block(str(h3), "H3", arxiv_url="H3URL", cfg=cfg)
    hc = h3.read_text()
    check("#2 h3-after-resources refreshes", "H3URL" in hc and "### Subsection" in hc and "body" in hc)

    # 🔒 #3: a method_name with traversal is sanitized (no file escapes tmp)
    ph.inject_resources_block(str(Path(tmp) / "trav.md"), "../../evil", arxiv_url="T", cfg=cfg)
    check("#3 traversal note didn't escape", not (Path(tmp).parent / "evil.md").exists()
          and not (Path(tmp).parent.parent / "evil.md").exists())


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
def test_review_fixes(tmp):
    print("review fixes (security / validation / version)")
    import prism_refs as pr

    # #3 safe_name
    check("#3 safe_name strips traversal", pc.safe_name("../../evil") == "evil")
    check("#3 safe_name strips slashes", "/" not in pc.safe_name("a/b/c"))
    check("#3 safe_name keeps good names", pc.safe_name("ViT-S") == "ViT-S" and pc.safe_name("S4++") == "S4++")
    check("#3 safe_name empty→untitled", pc.safe_name("..") == "untitled")

    # #4 figure-url allowlist (pure, no network)
    check("#4 allow arxiv https", ph._is_allowed_fig_url("https://arxiv.org/html/2312.00752/x1.png"))
    check("#4 allow arxiv subdomain", ph._is_allowed_fig_url("https://export.arxiv.org/x.png"))
    check("#4 block file://", not ph._is_allowed_fig_url("file:///etc/passwd.png"))
    check("#4 block off-host", not ph._is_allowed_fig_url("http://169.254.169.254/x.png"))
    check("#4 block protocol-relative", not ph._is_allowed_fig_url("//evil.com/x.png"))
    # download_figures must skip malicious srcs without fetching
    figs = [{"src": "file:///etc/passwd.png", "caption": ""},
            {"src": "http://169.254.169.254/x.png", "caption": ""}]
    got = ph.download_figures("2312.00752", figs, str(Path(tmp) / "figs"))
    check("#4 malicious srcs blocked", all(g["ok"] is False and g["reason"] == "blocked_url" for g in got))

    # #15 arxiv id validation
    check("#15 valid new id", ph._valid_arxiv_id("2312.00752v2"))
    check("#15 valid old id", ph._valid_arxiv_id("cs/0501001"))
    check("#15 reject traversal id", not ph._valid_arxiv_id("../../x"))
    check("#15 reject userinfo id", not ph._valid_arxiv_id("@evil.com/x"))

    # #8 old-style arxiv regex no longer matches arbitrary word/7digits
    ids = pr.extract_arxiv_ids("see data-set/1234567 and path/0000001 and cs/0501001")
    check("#8 bogus archive rejected", "data-set/1234567" not in ids and "path/0000001" not in ids)
    check("#8 real archive kept", "cs/0501001" in ids)

    # #12 _mini_yaml: '#' inside a quoted value is preserved
    check("#12 quoted hash kept", ph._strip_inline_comment('title: "a # b"  # real') == 'title: "a # b"  ')
    mm = ph._mini_yaml('papers:\n  - id: x\n    title: "has # hash"\n    arxiv: "1"\n')
    check("#12 mini-yaml keeps hash", mm["papers"][0]["title"] == "has # hash")

    # #6 queue validation raises on bad input
    def _q(body):
        f = Path(tmp) / "qv.yaml"; f.write_text(body); return f
    for label, body in [
        ("bad notes_strategy", "notes_strategy: nope\npapers:\n  - id: a\n    arxiv: \"1\"\n"),
        ("parallel out of range", "parallel: 99\npapers:\n  - id: a\n    arxiv: \"1\"\n"),
        ("path not pdf", "papers:\n  - id: a\n    path: /x/y.txt\n"),
        ("method has space", "papers:\n  - id: a\n    arxiv: \"1\"\n    method_name: My Method\n"),
    ]:
        try:
            ph.parse_paper_queue(str(_q(body)))
            check(f"#6 reject {label}", False, "no error")
        except ValueError:
            check(f"#6 reject {label}", True)
    # #6 empty/comment-only file → no crash, empty queue
    check("#6 empty papers ok", ph.parse_paper_queue(str(_q("papers:\n")))["papers"] == [])
    check("#6 comment-only ok", ph.parse_paper_queue(str(_q("# just a comment\n")))["papers"] == [])

    # #7 skip + defaults
    q = ph.parse_paper_queue(str(_q(
        'default_priority: P3\npapers:\n'
        '  - id: a\n    arxiv: "1"\n'
        '  - id: b\n    arxiv: "2"\n    skip: true\n')))
    check("#7 skip drops paper", [p["id"] for p in q["papers"]] == ["a"])
    check("#7 default_priority applied", q["papers"][0]["priority"] == "P3")

    # #11 schema_version: an old/missing-version state file is reset
    import prism_state as ps
    cfg = pc.load_config(path="/nonexistent"); cfg["vault_path"] = tmp; cfg["notes_folder"] = "p"
    sp = ps.state_path("VerProj", cfg); sp.parent.mkdir(parents=True, exist_ok=True)
    sp.write_text(json.dumps({"project": "VerProj", "papers": {"Old": {"status": "done"}}}))  # no schema_version
    st = ps.load_state("VerProj", cfg)
    check("#11 old-schema state reset", st["papers"] == {} and st["schema_version"] == pc.SCHEMA_VERSION)
    ps.update_paper("VerProj", "X", cfg, status="done")
    check("#11 new state stamped", json.loads(sp.read_text())["schema_version"] == pc.SCHEMA_VERSION)


def test_zotero(tmp):
    print("zotero (synthetic sqlite)")
    import sqlite3
    import zotero as zt
    db = Path(tmp) / "zotero.sqlite"
    storage = Path(tmp) / "storage"
    (storage / "ATTACHKEY").mkdir(parents=True)
    (storage / "ATTACHKEY" / "mamba.pdf").write_bytes(b"%PDF-1.4")
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE collections(collectionID INT, collectionName TEXT, parentCollectionID INT);
        CREATE TABLE collectionItems(collectionID INT, itemID INT);
        CREATE TABLE items(itemID INT, key TEXT, itemTypeID INT);
        CREATE TABLE itemData(itemID INT, fieldID INT, valueID INT);
        CREATE TABLE itemDataValues(valueID INT, value TEXT);
        CREATE TABLE fields(fieldID INT, fieldName TEXT);
        CREATE TABLE itemAttachments(itemID INT, parentItemID INT, contentType TEXT, path TEXT);
        INSERT INTO collections VALUES (1,'CIL',NULL),(2,'Sub',1);
        INSERT INTO fields VALUES (1,'title'),(2,'date');
        INSERT INTO items VALUES (10,'PAPERKEY',2),(11,'ATTACHKEY',14);
        INSERT INTO itemData VALUES (10,1,100),(10,2,101);
        INSERT INTO itemDataValues VALUES (100,'Mamba: Linear-Time'),(101,'2023-12-01');
        INSERT INTO collectionItems VALUES (1,10);
        INSERT INTO itemAttachments VALUES (11,10,'application/pdf','storage:mamba.pdf');
        """
    )
    con.commit(); con.close()

    cfg_file = Path(tmp) / "zcfg.json"
    cfg_file.write_text(json.dumps({"zotero_db": str(db), "zotero_storage": str(storage)}))
    os.environ["PRISM_CONFIG"] = str(cfg_file)
    try:
        cols = {c["name"]: c for c in zt.list_collections()}
        check("zotero list_collections", "CIL" in cols and cols["CIL"]["count"] == 1)
        papers = zt.papers_in_collection(1)
        check("zotero papers_in_collection", len(papers) == 1 and papers[0]["title"].startswith("Mamba"))
        check("zotero excludes attachments (itemTypeID 14)", all(p["item_id"] != 11 for p in papers))
        check("zotero pdf_path resolves", zt.pdf_path(10) == str(storage / "ATTACHKEY" / "mamba.pdf"))
        check("zotero search", zt.search("Mamba")[0]["item_id"] == 10)
        q = zt.zotero_collection_to_queue(1, recursive=False, project="Z")
        check("zotero→queue", len(q) == 1 and q[0]["zotero_item"] == 10 and q[0]["path"].endswith("mamba.pdf"))
    finally:
        del os.environ["PRISM_CONFIG"]


def test_marp_missing(tmp):
    print("marp missing-binary branch")
    import shutil as _sh
    real = _sh.which
    _sh.which = lambda name: None  # simulate marp absent
    try:
        ph.marp_render(str(Path(tmp) / "x.md"), str(tmp))
        check("marp missing raises", False, "no error")
    except RuntimeError as e:
        check("marp missing raises", "marp not found" in str(e))
    finally:
        _sh.which = real


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
        test_review_fixes(tmp)
        test_zotero(tmp)
        test_marp_missing(tmp)

    print()
    if _failures:
        print(f"FAILED {len(_failures)} / {_passed + len(_failures)}")
        for f in _failures:
            print("  -", f)
        sys.exit(1)
    print(f"OK — {_passed} checks passed")


if __name__ == "__main__":
    main()
