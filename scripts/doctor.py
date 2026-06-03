#!/usr/bin/env python3
"""paper-prism · dependency doctor.

Checks that every required and optional dependency is available, then reports
a clean checklist with ✓ / ✗ / ⚠ symbols. Exits 0 when all *required* deps
are satisfied (missing optional deps are warnings, not failures). Exits 1 if
any required dep is missing.

Usage (standalone):
    python3 scripts/doctor.py
    python3 scripts/doctor.py --repo-dir /path/to/paper-prism/repo

Called automatically by install.sh; also useful to run at any time to
diagnose a broken setup.
"""
from __future__ import annotations

import argparse
import importlib
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Symbols and helpers
# ---------------------------------------------------------------------------
OK   = "✓"   # ✓
FAIL = "✗"   # ✗
WARN = "⚠"   # ⚠

_required_missing: list[str] = []
_optional_missing: list[str] = []


def _ok(label: str, note: str = "") -> None:
    suffix = f"  ({note})" if note else ""
    print(f"  {OK}  {label}{suffix}")


def _fail(label: str, fix: str = "") -> None:
    _required_missing.append(label)
    print(f"  {FAIL}  {label}  [REQUIRED — missing]")
    if fix:
        for line in fix.strip().splitlines():
            print(f"       {line}")


def _warn(label: str, fix: str = "", note: str = "") -> None:
    _optional_missing.append(label)
    suffix = f"  ({note})" if note else ""
    print(f"  {WARN}  {label}  [optional — missing]{suffix}")
    if fix:
        for line in fix.strip().splitlines():
            print(f"       {line}")


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_python_version() -> None:
    """Python 3.10+ is required (match-statement, ParamSpec, newer typing)."""
    v = sys.version_info
    label = f"python3 >= 3.10  (found {v.major}.{v.minor}.{v.micro})"
    if v >= (3, 10):
        _ok(label)
    else:
        _fail(
            label,
            "Install Python 3.10+ via https://python.org or your package manager:\n"
            "  macOS:  brew install python@3.12\n"
            "  Debian/Ubuntu:  sudo apt install python3.12",
        )


def check_pdftoppm() -> None:
    """pdftoppm (poppler) is required to render PDF pages to PNG for table screenshots."""
    if shutil.which("pdftoppm"):
        _ok("pdftoppm (poppler)")
    else:
        _fail(
            "pdftoppm (poppler)",
            "macOS:  brew install poppler\n"
            "Debian/Ubuntu:  sudo apt install poppler-utils\n"
            "Fedora/RHEL:    sudo dnf install poppler-utils",
        )


def check_node() -> None:
    """node is required as the runtime for marp-cli."""
    if shutil.which("node"):
        _ok("node (Node.js)")
    else:
        _fail(
            "node (Node.js)",
            "macOS:  brew install node\n"
            "or install from https://nodejs.org (LTS recommended)",
        )


def check_marp() -> None:
    """marp-cli is required to render .slides.md → PDF + PPTX."""
    if shutil.which("marp"):
        _ok("marp (@marp-team/marp-cli)")
    else:
        _fail(
            "marp (@marp-team/marp-cli)",
            "npm i -g @marp-team/marp-cli\n"
            "(requires node — install that first if missing above)",
        )


def check_pillow() -> None:
    """Pillow (PIL) is required for crop_region() — table screenshot extraction."""
    try:
        from PIL import Image  # noqa: F401
        import PIL
        version = getattr(PIL, "__version__", "unknown")
        _ok(f"Pillow (PIL)  v{version}")
    except ImportError:
        _fail(
            "Pillow (PIL)",
            "pip install Pillow\n"
            "  or:  pip3 install Pillow",
        )


def check_pyyaml() -> None:
    """PyYAML enables full YAML queue parsing. paper-prism has a built-in fallback for
    the documented subset, so this is optional — but recommended for complex queues."""
    try:
        import yaml  # noqa: F401
        import yaml as _yaml
        version = getattr(_yaml, "__version__", "unknown")
        _ok(f"PyYAML  v{version}")
    except ImportError:
        _warn(
            "PyYAML",
            "pip install PyYAML",
            note="built-in fallback handles the documented queue subset without it",
        )


def check_pandoc() -> None:
    """pandoc provides a beamer-slide fallback when marp is unavailable."""
    if shutil.which("pandoc"):
        _ok("pandoc (beamer fallback)")
    else:
        _warn(
            "pandoc",
            "macOS:  brew install pandoc\n"
            "Debian/Ubuntu:  sudo apt install pandoc",
            note="only needed as beamer fallback if marp is absent",
        )


def check_config(repo_dir: Path) -> None:
    """Inspect the resolved paper-prism config and report vault/zotero path status."""
    assets_dir = repo_dir / "skills" / "paper-prism" / "assets"
    if not assets_dir.is_dir():
        print(f"  {WARN}  paper-prism config  [cannot locate assets dir: {assets_dir}]")
        _optional_missing.append("paper-prism config")
        return

    # Add assets to path so prism_config imports cleanly.
    sys.path.insert(0, str(assets_dir))
    try:
        # Fresh import each time (handles repeated calls in tests).
        import importlib
        if "prism_config" in sys.modules:
            prism_config = importlib.reload(sys.modules["prism_config"])
        else:
            prism_config = importlib.import_module("prism_config")

        cfg = prism_config.load_config()
        source = cfg.get("_config_source", "(unknown)")

        print(f"  {OK}  paper-prism config loaded")
        print(f"       source:  {source}")

        # vault_path
        vault = Path(cfg.get("vault_path", "")).expanduser()
        if vault.exists():
            print(f"       {OK}  vault_path exists:  {vault}")
        else:
            print(f"       {WARN}  vault_path not found:  {vault}")
            print(f"            Edit config.json and set vault_path to your Obsidian vault.")
            _optional_missing.append("vault_path")

        # zotero_db (optional feature)
        zotero_db = Path(cfg.get("zotero_db", "")).expanduser()
        if zotero_db.exists():
            print(f"       {OK}  zotero_db exists:  {zotero_db}")
        else:
            print(f"       {WARN}  zotero_db not found:  {zotero_db}")
            print(f"            (optional — only needed for Zotero input modes)")

    except Exception as exc:  # noqa: BLE001
        print(f"  {WARN}  paper-prism config  [error loading: {exc}]")
        _optional_missing.append("paper-prism config")
    finally:
        # Don't pollute sys.path for subsequent imports.
        if str(assets_dir) in sys.path:
            sys.path.remove(str(assets_dir))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="paper-prism dependency checker — exits 1 if required deps are missing.",
    )
    ap.add_argument(
        "--repo-dir",
        default=None,
        help="Path to the paper-prism repo root (default: parent of this script's directory).",
    )
    args = ap.parse_args()

    # Resolve repo root: --repo-dir flag > parent of scripts/ > cwd.
    if args.repo_dir:
        repo_dir = Path(args.repo_dir).expanduser().resolve()
    else:
        repo_dir = Path(__file__).resolve().parent.parent

    print()
    print("  paper-prism · dependency check")
    print("  " + "─" * 54)

    # ── Required ──────────────────────────────────────────────
    print()
    print("  REQUIRED")
    check_python_version()
    check_pdftoppm()
    check_node()
    check_marp()
    check_pillow()

    # ── Optional ──────────────────────────────────────────────
    print()
    print("  OPTIONAL")
    check_pyyaml()
    check_pandoc()

    # ── Config ────────────────────────────────────────────────
    print()
    print("  CONFIG")
    check_config(repo_dir)

    # ── Summary ───────────────────────────────────────────────
    print()
    print("  " + "─" * 54)
    if _required_missing:
        print(f"  {FAIL}  REQUIRED: {len(_required_missing)} missing:  {', '.join(_required_missing)}")
        print()
        print("  Install the items above, then re-run:")
        print(f"    python3 {Path(__file__).relative_to(repo_dir)}")
        print()
        sys.exit(1)
    else:
        print(f"  {OK}  REQUIRED: all good")
        if _optional_missing:
            print(
                f"  {WARN}  optional missing ({len(_optional_missing)}): "
                f"{', '.join(_optional_missing)}"
            )
        print()


if __name__ == "__main__":
    main()
