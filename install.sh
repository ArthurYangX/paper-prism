#!/usr/bin/env bash
# prism · installer
#
# What this does:
#   1. Symlinks ~/.claude/skills/prism -> this repo's skills/prism directory.
#   2. Copies config.example.json -> config.json if no config exists yet.
#   3. Runs the dependency doctor (scripts/doctor.py).
#
# Usage:
#   bash install.sh
#   (or:  chmod +x install.sh && ./install.sh)
#
# Requirements: bash 3.2+, python3. No sudo. No auto-install of deps.

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve this repo's root, regardless of where the script is called from.
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SRC="$SCRIPT_DIR/skills/prism"
SKILL_LINK="$HOME/.claude/skills/prism"
CONFIG_SRC="$SKILL_SRC/assets/config.example.json"
CONFIG_DST="$SKILL_SRC/assets/config.json"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║              prism  ·  installer                     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ---------------------------------------------------------------------------
# 1. Create ~/.claude/skills/ if it doesn't exist yet.
# ---------------------------------------------------------------------------
if [[ ! -d "$HOME/.claude/skills" ]]; then
    echo "  Creating ~/.claude/skills/ ..."
    mkdir -p "$HOME/.claude/skills"
fi

# ---------------------------------------------------------------------------
# 2. Symlink ~/.claude/skills/prism -> $SCRIPT_DIR/skills/prism
#    Safe logic: skip if already correct; warn and bail if occupied by something
#    else (real dir or symlink to a different target).
# ---------------------------------------------------------------------------
if [[ -e "$SKILL_LINK" || -L "$SKILL_LINK" ]]; then
    # Path already exists — figure out what it is.
    if [[ -L "$SKILL_LINK" ]]; then
        existing_target="$(readlink "$SKILL_LINK")"
        if [[ "$existing_target" == "$SKILL_SRC" ]]; then
            echo "  ✓  ~/.claude/skills/prism already points to this repo — nothing to do."
        else
            echo ""
            echo "  ✗  WARNING: ~/.claude/skills/prism already exists as a symlink"
            echo "     but it points somewhere else:"
            echo "     → $existing_target"
            echo ""
            echo "  To reinstall, remove it manually:"
            echo "     rm ~/.claude/skills/prism"
            echo "  Then re-run this script."
            echo ""
            exit 1
        fi
    else
        # It's a real directory (or some other non-symlink file).
        echo ""
        echo "  ✗  WARNING: ~/.claude/skills/prism already exists as a real directory."
        echo "     prism will NOT overwrite it automatically."
        echo ""
        echo "  To reinstall, remove it manually:"
        echo "     rm -rf ~/.claude/skills/prism"
        echo "  Then re-run this script."
        echo ""
        exit 1
    fi
else
    ln -s "$SKILL_SRC" "$SKILL_LINK"
    echo "  ✓  Linked:  ~/.claude/skills/prism"
    echo "         →  $SKILL_SRC"
fi

# ---------------------------------------------------------------------------
# 3. Copy config.example.json -> config.json if the user doesn't have one yet.
# ---------------------------------------------------------------------------
if [[ ! -f "$CONFIG_DST" ]]; then
    echo ""
    echo "  Copying config.example.json → config.json ..."
    cp "$CONFIG_SRC" "$CONFIG_DST"
    echo "  ✓  Created: $CONFIG_DST"
    echo ""
    echo "  ┌─────────────────────────────────────────────────────────────┐"
    echo "  │  ACTION REQUIRED: edit config.json before using prism.      │"
    echo "  │                                                               │"
    echo "  │  Key fields to set:                                          │"
    echo "  │    vault_path    — absolute path to your Obsidian vault      │"
    echo "  │    zotero_db     — path to ~/Zotero/zotero.sqlite            │"
    echo "  │    zotero_storage — path to ~/Zotero/storage/               │"
    echo "  │                                                               │"
    echo "  │  vault_path and zotero_* may be left as defaults if you      │"
    echo "  │  don't use those features yet.                               │"
    echo "  │                                                               │"
    echo "  │  Open with:                                                   │"
    echo "  │    \$EDITOR $CONFIG_DST"
    echo "  └─────────────────────────────────────────────────────────────┘"
else
    echo "  ✓  config.json already exists — not overwriting."
fi

# ---------------------------------------------------------------------------
# 4. Run the dependency doctor.
# ---------------------------------------------------------------------------
echo ""
echo "  Running dependency check ..."
echo "  ──────────────────────────────────────────────────────────────"
echo ""
python3 "$SCRIPT_DIR/scripts/doctor.py" --repo-dir "$SCRIPT_DIR" || true
# We use `|| true` so install.sh always exits 0 after the doctor runs.
# The doctor itself exits 1 if required deps are missing — the user sees the
# report and can decide what to fix; we don't want the whole script to abort
# before printing the usage instructions below.

# ---------------------------------------------------------------------------
# 5. Done — tell the user how to use prism.
# ---------------------------------------------------------------------------
echo ""
echo "  ──────────────────────────────────────────────────────────────"
echo ""
echo "  ✅ prism is installed."
echo ""
echo "  HOW TO USE"
echo "  ──────────"
echo "  Open Claude Code in any project, then say:"
echo ""
echo "    \"read paper.pdf and make a deck\""
echo "    \"analyze this paper: arxiv:2312.00752\""
echo "    \"batch process ~/papers/ into project ViT\""
echo "    \"read my Zotero 'CIL' collection\""
echo ""
echo "  If you haven't edited config.json yet, do that first:"
echo "    \$EDITOR $CONFIG_DST"
echo ""
echo "  Full documentation: $SCRIPT_DIR/README.md"
echo ""
