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
    cp "$CONFIG_SRC" "$CONFIG_DST"
    echo ""
    echo "  ✓  Created: $CONFIG_DST"
    # vault_path is the ONE setting that matters. Everything else (Zotero paths,
    # models, parallel, lang, ...) has a working default. Capture vault_path here
    # so the user never has to open the JSON by hand.
    DEFAULT_VAULT="$HOME/Documents/Obsidian Vault"
    if [[ -t 0 && -t 1 ]]; then
        echo ""
        read -r -p "  Your Obsidian vault path [$DEFAULT_VAULT] (blank = skip, set later): " VAULT_IN
        VAULT_PATH="${VAULT_IN:-$DEFAULT_VAULT}"
        if [[ -n "$VAULT_IN" || -d "$DEFAULT_VAULT" ]]; then
            python3 - "$CONFIG_DST" "$VAULT_PATH" <<'PY'
import json, sys
path, vault = sys.argv[1], sys.argv[2]
cfg = json.load(open(path))
cfg["vault_path"] = vault
with open(path, "w") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
    f.write("\n")
print(f"  ✓  vault_path set to: {vault}")
PY
        else
            echo "  ℹ  No vault set yet — edit vault_path in $CONFIG_DST when you have one."
        fi
    else
        echo "  (non-interactive run: vault_path left at its default — edit $CONFIG_DST to change it)"
    fi
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
echo "  Tune anything else (language, Zotero paths, parallelism) in:"
echo "    $CONFIG_DST"
echo "    — optional; every field has a working default."
echo ""
echo "  Full documentation: $SCRIPT_DIR/README.md"
echo ""
