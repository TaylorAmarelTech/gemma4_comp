#!/usr/bin/env bash
# Non-destructive PII purge: build a sibling clone of the repo with
# PII-bearing paths stripped from ALL of git history, then verify it
# matches the latest clean state.
#
# This script does NOT touch:
#   - the source repo working tree
#   - the source repo .git/
#   - the source repo's remote
#   - any local clone you have elsewhere
#
# It produces a fresh clone at ../gemma4_comp_clean/ that you can
# then push to a NEW remote, swap remotes, or just keep as a
# verified-clean backup. You decide later — this is purely additive.
#
# Usage:
#     bash scripts/build_pii_clean_mirror.sh
#
# Then inspect:
#     cd ../gemma4_comp_clean
#     git log --oneline | head -20
#     git log --all --diff-filter=D -- 'data/drive_text_cache/*'  # should be empty (path never existed)
#     ls -la data/                                                  # no drive_* files
#     bash scripts/run_smoke_tests.sh                               # tests still pass

set -euo pipefail

SOURCE_REPO="$(cd "$(dirname "$0")/.." && pwd)"
PARENT_DIR="$(dirname "$SOURCE_REPO")"
CLEAN_DIR="$PARENT_DIR/gemma4_comp_clean"

# Use the user-installed git-filter-repo (Python 3.10 install)
FILTER_REPO="/c/Users/amare/AppData/Roaming/Python/Python310/Scripts/git-filter-repo.exe"
if ! [ -x "$FILTER_REPO" ]; then
    if command -v git-filter-repo >/dev/null 2>&1; then
        FILTER_REPO="git-filter-repo"
    else
        echo "ERROR: git-filter-repo not found." >&2
        echo "Install with: py -3.10 -m pip install --user git-filter-repo" >&2
        exit 1
    fi
fi

echo "=== Non-destructive PII purge ==="
echo "Source repo:  $SOURCE_REPO"
echo "Clean mirror: $CLEAN_DIR"
echo "Filter tool:  $FILTER_REPO"
echo ""

if [ -e "$CLEAN_DIR" ]; then
    echo "ERROR: Target $CLEAN_DIR already exists." >&2
    echo "Move or rename it before re-running:" >&2
    echo "  mv \"$CLEAN_DIR\" \"$CLEAN_DIR.\$(date +%s).bak\"" >&2
    exit 1
fi

# Step 1: Clone the source repo (uses git's hardlinks for objects on
# same filesystem — fast and disk-cheap, but the clone is fully
# independent: rewriting history in the clone has no effect on source).
echo "[1/5] Cloning source → mirror..."
git clone --no-local "$SOURCE_REPO" "$CLEAN_DIR"
echo "      Done."
echo ""

# Step 2: Strip the PII-bearing paths from ALL of history in the clone.
# --invert-paths means "remove THESE paths"; the rest of the repo
# (every commit, every file, every branch) is preserved.
echo "[2/5] Stripping PII paths from all of clone history..."
cd "$CLEAN_DIR"
"$FILTER_REPO" --force \
    --path data/drive_text_cache/ \
    --path data/drive_image_cache/ \
    --path-glob 'data/drive_*.json' \
    --path-glob 'data/drive_*.md' \
    --path-glob 'data/drive_*.npz' \
    --path-glob 'data/_drive_*' \
    --path-glob 'data/_curated_drive_*' \
    --invert-paths
echo "      Done."
echo ""

# Step 3: Sanity-check — verify the cleaned paths are gone from
# the clone's history.
echo "[3/5] Verifying PII paths are gone from clone history..."
RESIDUAL=$(git log --all --raw --pretty=format: -- \
    'data/drive_text_cache/' 'data/drive_image_cache/' \
    'data/drive_*.json' 'data/drive_*.md' 'data/_drive_*' \
    2>/dev/null | grep -c '.' || true)
if [ "$RESIDUAL" -eq 0 ]; then
    echo "      OK: 0 historical references to PII paths remain in clone."
else
    echo "      WARN: $RESIDUAL residual references found. Inspect with:"
    echo "          cd $CLEAN_DIR && git log --all --raw -- 'data/drive_*'"
fi
echo ""

# Step 4: Grep the entire clone history for known leaked names to
# confirm they're gone from the object database too.
echo "[4/5] Verifying known leaked names are gone from clone object db..."
LEAKED_HITS=0
for NAME in "Jessica Sumpio" "Funnylen Tanamor" "Meliza Salamanca" "Vimadel Ladores"; do
    HITS=$(git log --all -p -S "$NAME" 2>/dev/null | grep -c "$NAME" || true)
    if [ "$HITS" -gt 0 ]; then
        echo "      WARN: '$NAME' still present in $HITS line(s) of clone history."
        LEAKED_HITS=$((LEAKED_HITS + HITS))
    fi
done
if [ "$LEAKED_HITS" -eq 0 ]; then
    echo "      OK: 0 known leaked names found in clone history."
fi
echo ""

# Step 5: Report state of the clean mirror.
echo "[5/5] Clean mirror state:"
echo "      Path:      $CLEAN_DIR"
echo "      Branch:    $(git rev-parse --abbrev-ref HEAD)"
echo "      Latest:    $(git log -1 --pretty='%h %s')"
echo "      History:   $(git log --oneline | wc -l) commits"
echo "      Size:      $(du -sh .git 2>/dev/null | cut -f1)"
echo ""
echo "Source repo at $SOURCE_REPO is UNTOUCHED."
echo ""
echo "=== Next steps (you decide) ==="
echo ""
echo "Option 1 — Push as a NEW GitHub repo (most non-destructive):"
echo "    cd $CLEAN_DIR"
echo "    gh repo create TaylorAmarelTech/duecare --public --source=. --push"
echo "    # Then update submission URLs to point to duecare;"
echo "    # archive (read-only) or delete the old gemma4_comp repo."
echo ""
echo "Option 2 — Swap remote on this clone, force-push to existing repo"
echo "          (destructive to public history but keeps the URL):"
echo "    cd $CLEAN_DIR"
echo "    git remote set-url origin https://github.com/TaylorAmarelTech/gemma4_comp.git"
echo "    git push origin master --force-with-lease"
echo "    # WARNING: anyone who has cloned the repo will have to"
echo "    #          re-clone or rebase. Their old SHAs become"
echo "    #          unreachable. The PII history is GONE from the"
echo "    #          public side."
echo ""
echo "Option 3 — Hold the clean mirror as a backup; do nothing further:"
echo "    # The clean mirror sits at $CLEAN_DIR until you decide."
echo "    # The original repo and its public history continue to"
echo "    # contain the PII. Add an audit note documenting this."
echo ""
echo "Recommendation: Option 1 if you want maximum safety; Option 2"
echo "if you want to keep the existing GitHub URL working."
