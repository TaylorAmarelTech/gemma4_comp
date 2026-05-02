#!/usr/bin/env bash
# Duecare restore — counterpart to backup.sh.
#
# Usage:
#   bash scripts/restore.sh backups/duecare-2026-05-02.tgz
#
# Stops the stack, restores the named volumes, restarts.

set -euo pipefail

ARCHIVE="${1:-}"
[[ -z "$ARCHIVE" ]] && { echo "Usage: $0 <backup.tgz>"; exit 1; }
[[ -f "$ARCHIVE" ]] || { echo "Not found: $ARCHIVE"; exit 1; }

ARCHIVE_ABS="$(realpath "$ARCHIVE")"

echo "Restoring from $ARCHIVE_ABS"
echo "  ⚠ This stops + REPLACES the current journal + audit + caddy state."
read -rp "  Type 'yes' to proceed: " confirm
[[ "$confirm" == "yes" ]] || { echo "Aborted."; exit 0; }

# Stop the stack
docker compose down

# Inspect archive — what volumes are inside?
TMPLIST=$(mktemp)
tar -tzf "$ARCHIVE_ABS" | head -20 > "$TMPLIST"

# Restore each volume
for VOL in duecare-data caddy-data caddy-config ollama-models; do
  if grep -q "^${VOL}/" "$TMPLIST" 2>/dev/null || \
     grep -q "^./${VOL}/" "$TMPLIST" 2>/dev/null; then
    echo "  ↻ restoring $VOL"
    docker volume rm "$VOL" 2>/dev/null || true
    docker volume create "$VOL" >/dev/null
    docker run --rm \
      -v "$VOL:/restore-target" \
      -v "$ARCHIVE_ABS:/backup.tgz:ro" \
      alpine sh -c "cd /restore-target && tar xzf /backup.tgz --strip-components=1 ${VOL}/ 2>/dev/null || tar xzf /backup.tgz --strip-components=2 ./${VOL}/"
  else
    echo "  · $VOL not in archive (skipping)"
  fi
done

# Restore .env if present
if tar -tzf "$ARCHIVE_ABS" | grep -q "^\.env$"; then
  if [[ -f .env ]]; then
    cp .env .env.before-restore
    echo "  ! existing .env saved as .env.before-restore"
  fi
  tar -xzf "$ARCHIVE_ABS" .env
  echo "  ↻ .env restored"
fi

rm -f "$TMPLIST"

echo
echo "  ✓ Restore complete. Bringing the stack back up:"
docker compose up -d
echo
echo "  Run 'bash scripts/duecare-doctor.sh' to verify health."
