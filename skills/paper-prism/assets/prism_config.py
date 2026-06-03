"""paper-prism · configuration and i18n labels.

A single place that resolves *where things live* (vault, Zotero, output
folders) and *what headings look like* (English or Chinese), so the rest of
paper-prism never hard-codes a personal path or a language.

Config resolution order (first hit wins):
    1. $PRISM_CONFIG                     (explicit path to a JSON file)
    2. ./config.json                     (next to this module)
    3. ~/.config/paper-prism/config.json       (XDG-style user config)
    4. built-in DEFAULTS                  (so paper-prism still imports with no config)

Every value can be overridden in the JSON file. `~` is expanded in all paths.

Usage:
    from prism_config import load_config, get_labels
    cfg = load_config()
    L = get_labels(cfg)
    print(cfg["vault_path"], L["resources_heading"])
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

__version__ = "0.1.0"
SCHEMA_VERSION = 1  # bump when the state-file / durable-cache format changes


def safe_name(name: str) -> str:
    """Filesystem-safe identifier for a method or project name.

    Keeps letters/digits/`. _ + -`, replaces anything else (path separators,
    spaces, colons) with `_`, neutralises `..`, and strips leading/trailing
    `.`/`_`. This is the defence-in-depth guard that prevents a paper-derived
    `method_name`/`project` from escaping the vault via `../` or an absolute path
    when it is interpolated into a path. Returns "untitled" if nothing survives.
    """
    s = re.sub(r"[^\w.+-]", "_", str(name))   # drops / \ : space etc.
    while ".." in s:
        s = s.replace("..", "_")
    s = s.strip("._")
    return s or "untitled"

# ---------------------------------------------------------------------------
# Defaults — paper-prism imports and runs even with no config file present.
# ---------------------------------------------------------------------------
DEFAULTS: dict[str, Any] = {
    # Where notes live
    "vault_path": "~/Documents/Obsidian Vault",
    "notes_folder": "papers",          # {vault}/{notes_folder}/
    "default_project": "Research",      # {vault}/{notes_folder}/{project}/
    "concepts_folder": "_concepts",     # {vault}/{notes_folder}/{concepts_folder}/
    "moc_folder": "_MOC",               # {vault}/{moc_folder}/
    "slides_subdir": "_slides",          # per-project deck folder name
    # Zotero (optional — only needed for Zotero input modes)
    "zotero_db": "~/Zotero/zotero.sqlite",
    "zotero_storage": "~/Zotero/storage",
    # Output language for generated headings: "en" or "zh"
    "lang": "en",
    # Optional per-key label overrides (merged over the lang preset)
    "labels": {},
    # Subagent model tiers (cost control)
    "models": {"analysis": "opus", "figures": "sonnet", "tables": "sonnet"},
    # Batch behaviour
    "parallel": 4,                       # papers per /loop iteration
    "concept_budget": 8,                 # max new [[concepts]] created per paper
    # Git automation (off by default — opt in)
    "git_commit": False,
    "git_push": False,
}

# Keys that hold filesystem paths (expanduser applied on load)
_PATH_KEYS = ("vault_path", "zotero_db", "zotero_storage")


# ---------------------------------------------------------------------------
# Label presets (i18n). English is the default; zh reproduces the original
# Obsidian-Chinese experience. Override individual keys via cfg["labels"].
# ---------------------------------------------------------------------------
LABELS_EN: dict[str, str] = {
    "note_title_prefix": "Paper Note: ",
    "resources_heading": "## Resources",
    "label_paper": "📄 Paper",
    "label_slides": "🎬 Slides",
    "label_zotero": "📦 Zotero",
    "label_arxiv": "🌐 arXiv",
    "label_code": "💻 Code",
    "label_project": "📁 Project",
    "label_index": "📚 Index",
    "tldr_heading": "## TL;DR",
    "contributions_heading": "## Key Contributions",
    "todo": "{todo}",
    "untriaged_folder": "_inbox",
    # Global slide library MOC
    "slides_moc_title": "# Slide Library",
    "slides_moc_note": "> Auto-maintained by paper-prism after each run.",
    "slides_moc_columns": "| Paper | Topic | Venue · Year | Preview |",
    # Project MOC reading-queue table
    "project_queue_columns": (
        "| # | Paper | Method | Category | Venue · Year | Status | Priority | Relevance |"
    ),
}

LABELS_ZH: dict[str, str] = {
    "note_title_prefix": "论文笔记：",
    "resources_heading": "## 资源",
    "label_paper": "📄 原论文",
    "label_slides": "🎬 幻灯片",
    "label_zotero": "📦 Zotero",
    "label_arxiv": "🌐 arXiv",
    "label_code": "💻 Code",
    "label_project": "📁 项目",
    "label_index": "📚 全局索引",
    "tldr_heading": "## 一句话总结",
    "contributions_heading": "## 核心贡献",
    "todo": "{待补}",
    "untriaged_folder": "_待整理",
    "slides_moc_title": "# 幻灯片库",
    "slides_moc_note": "> 自动维护：paper-prism 每篇处理完成后追加 / 更新。",
    "slides_moc_columns": "| 论文 | 主题 | Venue · Year | 幻灯预览 |",
    "project_queue_columns": (
        "| # | 论文 | 方法 | 定位分类 | Venue · Year | 状态 | 跟进 | 与项目的关系 |"
    ),
}

_PRESETS = {"en": LABELS_EN, "zh": LABELS_ZH}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def _config_search_paths() -> list[Path]:
    here = Path(__file__).resolve().parent
    paths: list[Path] = []
    env = os.environ.get("PRISM_CONFIG")
    if env:
        paths.append(Path(env).expanduser())
    paths.append(here / "config.json")
    paths.append(Path("~/.config/paper-prism/config.json").expanduser())
    return paths


def load_config(path: str | None = None) -> dict[str, Any]:
    """Return merged config: DEFAULTS overlaid with the first config file found.

    Path keys are expanduser-expanded. Pass `path` to force a specific file.
    """
    cfg: dict[str, Any] = json.loads(json.dumps(DEFAULTS))  # deep copy
    candidates = [Path(path).expanduser()] if path else _config_search_paths()
    for p in candidates:
        if p.is_file():
            user = json.loads(p.read_text())
            cfg = _deep_merge(cfg, user)
            cfg["_config_source"] = str(p)
            break
    else:
        cfg["_config_source"] = "(defaults — no config file found)"
    for k in _PATH_KEYS:
        if k in cfg and isinstance(cfg[k], str):
            cfg[k] = str(Path(cfg[k]).expanduser())
    return cfg


def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def get_labels(cfg: dict[str, Any] | None = None) -> dict[str, str]:
    """Return the label set for cfg['lang'], with cfg['labels'] overrides applied."""
    cfg = cfg or load_config()
    preset = _PRESETS.get(cfg.get("lang", "en"), LABELS_EN)
    labels = dict(preset)
    labels.update(cfg.get("labels", {}) or {})
    return labels


# ---------------------------------------------------------------------------
# Derived paths
# ---------------------------------------------------------------------------
def notes_path(cfg: dict[str, Any] | None = None) -> Path:
    cfg = cfg or load_config()
    return Path(cfg["vault_path"]).expanduser() / cfg["notes_folder"]


def project_path(project: str | None = None, cfg: dict[str, Any] | None = None) -> Path:
    cfg = cfg or load_config()
    return notes_path(cfg) / safe_name(project or cfg["default_project"])


def concepts_path(cfg: dict[str, Any] | None = None) -> Path:
    cfg = cfg or load_config()
    return notes_path(cfg) / cfg["concepts_folder"]


def slides_moc_path(cfg: dict[str, Any] | None = None) -> Path:
    cfg = cfg or load_config()
    return Path(cfg["vault_path"]).expanduser() / cfg["moc_folder"] / "Slide Library.md"


def project_moc_path(project: str | None = None, cfg: dict[str, Any] | None = None) -> Path:
    cfg = cfg or load_config()
    proj = safe_name(project or cfg["default_project"])
    return project_path(proj, cfg) / f"00 {proj}.md"


if __name__ == "__main__":  # quick introspection: `python3 prism_config.py`
    import pprint
    c = load_config()
    print("config source:", c.get("_config_source"))
    print("vault_path   :", c["vault_path"])
    print("notes_path   :", notes_path(c))
    print("lang         :", c["lang"])
    print("labels:")
    pprint.pprint(get_labels(c))
