"""paper-prism · checkpoint / resume state.

Batch processing must survive interruptions — a crash, a `/loop` stop, a laptop
lid. paper-prism keeps two things durable so any re-run picks up exactly where it left
off, per paper and per phase:

1. A per-project **state file** (`{project}/.prism_state.json`) recording each
   paper's status and which pipeline phases completed.
2. A per-paper **durable cache** (`{deck_dir}/.cache/`) holding the intermediate
   artifacts (twelve-Q analysis, note body, figure/table maps) so a half-finished
   paper resumes without re-running the expensive Phase-2 subagents.

`resume_plan()` is the heart: given a paper, it inspects the durable artifacts +
state and returns which phases may be skipped. The pipeline consults it in Phase
1 and only does the work that's actually missing. All writes are atomic
(temp-file + os.replace) so an interrupted write never corrupts the state file.

Phases (in order): analysis · figures · tables · synth · render · bind.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prism_config import load_config, project_path, SCHEMA_VERSION  # noqa: E402

PHASES = ("analysis", "figures", "tables", "synth", "render", "bind")
_DONE_MIN_PDF_BYTES = 50 * 1024  # a real deck is comfortably bigger than this


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# State file
# ---------------------------------------------------------------------------
def state_path(project: str, cfg: dict[str, Any] | None = None) -> Path:
    cfg = cfg or load_config()
    return project_path(project, cfg) / ".prism_state.json"


def _skeleton(project: str) -> dict:
    return {"schema_version": SCHEMA_VERSION, "project": project,
            "updated": None, "papers": {}}


def load_state(project: str, cfg: dict[str, Any] | None = None) -> dict:
    """Load the project state file, or a fresh skeleton if absent / corrupt /
    written by an incompatible paper-prism version (schema_version mismatch → reset)."""
    p = state_path(project, cfg)
    if p.is_file():
        try:
            data = json.loads(p.read_text())
            if isinstance(data, dict) and data.get("schema_version") == SCHEMA_VERSION:
                return data
            # missing/old schema → don't trust it; start fresh (resume re-runs).
        except (json.JSONDecodeError, OSError):
            pass
    return _skeleton(project)


def save_state(state: dict, project: str, cfg: dict[str, Any] | None = None) -> None:
    """Atomically write the state file (temp + os.replace)."""
    p = state_path(project, cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    state["schema_version"] = SCHEMA_VERSION
    state["updated"] = _now()
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def update_paper(
    project: str,
    method: str,
    cfg: dict[str, Any] | None = None,
    *,
    status: str | None = None,        # queued | in_progress | done | failed
    phase_done: str | None = None,    # one of PHASES — marks it complete
    error: str | None = None,
    **extra: Any,
) -> dict:
    """Read-modify-write one paper's entry. Returns the updated state.

    Idempotent and safe under repeated calls; the caller doesn't manage the file.
    """
    state = load_state(project, cfg)
    rec = state["papers"].setdefault(method, {"status": "queued", "phases": {}, "updated": None})
    if status is not None:
        rec["status"] = status
    if phase_done is not None:
        if phase_done not in PHASES:
            raise ValueError(f"unknown phase {phase_done!r}; expected one of {PHASES}")
        rec.setdefault("phases", {})[phase_done] = True
    if error is not None:
        rec["error"] = error
    elif status == "done":
        rec["error"] = None
    rec.update(extra)
    rec["updated"] = _now()
    save_state(state, project, cfg)
    return state


def paper_status(project: str, method: str, cfg: dict[str, Any] | None = None) -> dict:
    """Return one paper's record (or a default queued record)."""
    return load_state(project, cfg)["papers"].get(
        method, {"status": "queued", "phases": {}, "updated": None})


# ---------------------------------------------------------------------------
# Durable per-paper cache (intermediate artifacts survive a crash)
# ---------------------------------------------------------------------------
def cache_dir(deck_dir: str) -> Path:
    """The durable intermediate-artifact dir for one paper. Created on demand."""
    d = Path(deck_dir) / ".cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def purge_cache(deck_dir: str) -> None:
    """Remove the durable cache — call only after a paper fully succeeds."""
    import shutil
    d = Path(deck_dir) / ".cache"
    if d.exists():
        shutil.rmtree(d, ignore_errors=True)


def _nonempty(p: Path) -> bool:
    return p.is_file() and p.stat().st_size > 0


# ---------------------------------------------------------------------------
# Resume logic
# ---------------------------------------------------------------------------
def is_paper_done(deck_dir: str, method: str) -> bool:
    """A paper is done if its slide deck PDF exists and is a real size.

    Cheap, filesystem-only check used by the batch dedup pass — no state file
    needed, so it works even on a vault paper-prism has never tracked.
    """
    pdf = Path(deck_dir) / f"{method}.slides.pdf"
    return pdf.is_file() and pdf.stat().st_size > _DONE_MIN_PDF_BYTES


def resume_plan(deck_dir: str, method: str) -> dict[str, bool]:
    """Inspect durable artifacts and report which phases can be SKIPPED.

    Returns {phase: skip_bool} for every phase. Purely artifact-driven (no state
    file dependency) so it's correct even after the state file is deleted.

        analysis  ← .cache/{m}_qa.md + .cache/{m}_note_body.md present
        figures   ← .cache/{m}_figmap.json present
        tables    ← .cache/{m}_tablemap.json present
        synth     ← {m}.slides.md present
        render    ← {m}.slides.pdf (real size) + {m}.slides.pptx present
        bind      ← only via the state file (MOC writes are idempotent anyway),
                    so resume_plan reports skip_bind=False; the binders are safe
                    to re-run.
    """
    d = Path(deck_dir)
    c = d / ".cache"
    pdf = d / f"{method}.slides.pdf"
    return {
        "analysis": _nonempty(c / f"{method}_qa.md") and _nonempty(c / f"{method}_note_body.md"),
        "figures": _nonempty(c / f"{method}_figmap.json"),
        "tables": _nonempty(c / f"{method}_tablemap.json"),
        "synth": _nonempty(d / f"{method}.slides.md"),
        "render": pdf.is_file() and pdf.stat().st_size > _DONE_MIN_PDF_BYTES
        and (d / f"{method}.slides.pptx").is_file(),
        "bind": False,
    }


def next_phase(deck_dir: str, method: str) -> str | None:
    """The first phase NOT yet complete (resume point), or None if all done."""
    plan = resume_plan(deck_dir, method)
    for ph in PHASES:
        if not plan.get(ph, False):
            return ph
    return None


# ---------------------------------------------------------------------------
# CLI:  python3 prism_state.py status <project>
#       python3 prism_state.py resume <deck_dir> <method>
# ---------------------------------------------------------------------------
def _main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "status":
        st = load_state(args[0])
        print(f"project: {st['project']}  updated: {st['updated']}")
        for m, rec in sorted(st["papers"].items()):
            done = sum(1 for p in PHASES if rec.get("phases", {}).get(p))
            print(f"  {rec['status']:<12} {m:<24} phases {done}/{len(PHASES)}"
                  + (f"  err={rec.get('error')}" if rec.get("error") else ""))
    elif cmd == "resume":
        plan = resume_plan(args[0], args[1])
        nxt = next_phase(args[0], args[1])
        print(json.dumps({"skip": plan, "resume_from": nxt}, ensure_ascii=False, indent=2))
    else:
        print(f"unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    _main()
