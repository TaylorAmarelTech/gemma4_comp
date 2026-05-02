#!/usr/bin/env bash
# Duecare backup — snapshots the journal + audit log + ollama model
# cache + Grafana dashboards into a single tar.gz.
#
# Usage:
#   bash scripts/backup.sh                      # → backups/duecare-YYYY-MM-DD.tgz
#   bash scripts/backup.sh --dest /mnt/usb      # custom destination
#   bash scripts/backup.sh --skip-models        # 90% smaller: skip Ollama cache
#
# Restore:
#   bash scripts/restore.sh backups/duecare-YYYY-MM-DD.tgz

set -euo pipefail

DEST="backups"
SKIP_MODELS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dest)         DEST="$2"; shift 2 ;;
    --skip-models)  SKIP_MODELS=1; shift ;;
    --help|-h)      grep '^#' "$0" | sed 's/^# //;s/^#//' | head -10; exit 0 ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

mkdir -p "$DEST"
STAMP=$(date +%F)
OUT="$DEST/duecare-$STAMP.tgz"

echo "Snapshotting Duecare state to $OUT"

# Volumes to back up. Skip ollama-models if --skip-models (90% size reduction).
VOLS=(duecare-data caddy-data caddy-config)
[[ $SKIP_MODELS -eq 0 ]] && VOLS+=(ollama-models)

# Use a throw-away alpine container to tar the named volumes.
ARGS=()
for v in "${VOLS[@]}"; do
  ARGS+=(-v "$v:/backup-source/$v:ro")
done

mkdir -p "$(realpath "$DEST")"
docker run --rm "${ARGS[@]}" \
  -v "$(realpath "$DEST"):/backup-out" \
  alpine sh -c "cd /backup-source && tar czf /backup-out/duecare-$STAMP.tgz ."

# Also include the .env (passwords / keys / model name) — operator
# may want to redact before sharing.
if [[ -f .env ]]; then
  tar -rf "$OUT" .env 2>/dev/null || \
    (gzip -d "$OUT" && tar -rf "${OUT%.tgz}.tar" .env && gzip "${OUT%.tgz}.tar" && mv "${OUT%.tgz}.tar.gz" "$OUT")
fi

SIZE=$(du -h "$OUT" | awk '{print $1}')
echo
echo "  ✓ Backup written: $OUT ($SIZE)"
echo
echo "  Contents:"
echo "    - duecare-data    (chat history, journal, audit log)"
echo "    - caddy-data      (TLS certs)"
echo "    - caddy-config    (caddy state)"
[[ $SKIP_MODELS -eq 0 ]] && echo "    - ollama-models   (~1.5 GB - 4 GB depending on which Gemma)"
echo "    - .env            (secrets — consider redacting before sharing)"
echo
echo "  Restore: bash scripts/restore.sh $OUT"
