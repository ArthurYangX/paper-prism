#!/usr/bin/env bash
# paper-prism · installer
#
# What this does:
#   1. Symlinks ~/.claude/skills/paper-prism -> this repo's skills/paper-prism directory.
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
SKILL_SRC="$SCRIPT_DIR/skills/paper-prism"
SKILL_LINK="$HOME/.claude/skills/paper-prism"
CONFIG_SRC="$SKILL_SRC/assets/config.example.json"
CONFIG_DST="$SKILL_SRC/assets/config.json"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║              paper-prism  ·  installer                     ║"
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
# 2. Symlink ~/.claude/skills/paper-prism -> $SCRIPT_DIR/skills/paper-prism
#    Safe logic: skip if already correct; warn and bail if occupied by something
#    else (real dir or symlink to a different target).
# ---------------------------------------------------------------------------
if [[ -e "$SKILL_LINK" || -L "$SKILL_LINK" ]]; then
    # Path already exists — figure out what it is.
    if [[ -L "$SKILL_LINK" ]]; then
        existing_target="$(readlink "$SKILL_LINK")"
        if [[ "$existing_target" == "$SKILL_SRC" ]]; then
            echo "  ✓  ~/.claude/skills/paper-prism already points to this repo — nothing to do."
        else
            echo ""
            echo "  ✗  WARNING: ~/.claude/skills/paper-prism already exists as a symlink"
            echo "     but it points somewhere else:"
            echo "     → $existing_target"
            echo ""
            echo "  To reinstall, remove it manually:"
            echo "     rm ~/.claude/skills/paper-prism"
            echo "  Then re-run this script."
            echo ""
            exit 1
        fi
    else
        # It's a real directory (or some other non-symlink file).
        echo ""
        echo "  ✗  WARNING: ~/.claude/skills/paper-prism already exists as a real directory."
        echo "     paper-prism will NOT overwrite it automatically."
        echo ""
        echo "  To reinstall, remove it manually:"
        echo "     rm -rf ~/.claude/skills/paper-prism"
        echo "  Then re-run this script."
        echo ""
        exit 1
    fi
else
    ln -s "$SKILL_SRC" "$SKILL_LINK"
    echo "  ✓  Linked:  ~/.claude/skills/paper-prism"
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
    echo "  │  ACTION REQUIRED: edit config.json before using paper-prism.      │"
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
# Capture the doctor's exit code (1 = required deps missing) WITHOUT aborting the
# script — we still print usage below, but we must not claim the install is "ready"
# when a required dependency is missing.
DOCTOR_OK=0
python3 "$SCRIPT_DIR/scripts/doctor.py" --repo-dir "$SCRIPT_DIR" || DOCTOR_OK=1

# ---------------------------------------------------------------------------
# 5. Done — tell the user how to use paper-prism.
# ---------------------------------------------------------------------------
echo ""
echo "  ──────────────────────────────────────────────────────────────"
echo ""
if [[ "$DOCTOR_OK" -eq 0 ]]; then
    echo "  ✅ paper-prism is installed and ready."
else
    echo "  ⚠️  paper-prism is installed, but NOT ready yet — a required dependency"
    echo "      is missing (see the doctor report above). Install it, then re-run"
    echo "      this script (or just \`python3 scripts/doctor.py\`) to confirm."
fi
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
