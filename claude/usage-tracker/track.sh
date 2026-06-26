#!/usr/bin/env bash
# track.sh — ingest the latest session transcripts and rebuild the dashboard.
# Usage: ./track.sh [--open] [--filter <substr>] [-- <extra ingest args>]
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OPEN=0; FILTER=()
while [ $# -gt 0 ]; do
  case "$1" in
    --open) OPEN=1; shift;;
    --filter) FILTER=(--filter "$2"); shift 2;;
    --) shift; break;;
    *) break;;
  esac
done
node "$DIR/ingest.js" ${FILTER[@]+"${FILTER[@]}"} "$@"
node "$DIR/build-dashboard.js"
[ "$OPEN" -eq 1 ] && { command -v open >/dev/null && open "$DIR/dashboard.html" || echo "open $DIR/dashboard.html"; }
echo "→ $DIR/dashboard.html"
