#!/usr/bin/env bash
# Preflight: run the same quality checks Husky runs locally and CI runs
# remotely. Designed to be invoked by the main agent before commit/PR,
# replacing the former `pr-preflight` subagent (demoted because this work
# is entirely mechanical — no model rental needed).
#
# Behavior:
#   1. Detect the project's package manager (pnpm > yarn > npm) and the
#      available scripts in package.json.
#   2. Run each gate command if the matching script exists:
#        - lint-staged (pre-commit equivalent)
#        - lint
#        - compile-ts / typecheck / tsc
#        - test
#   3. Exit 0 on PASS, non-zero on first failure (or aggregate fail at end
#      with --keep-going).
#   4. Always print a short summary at the end: which steps ran, which
#      passed, which failed.
#
# The main agent calls this and interprets the output. It does NOT need to
# decide what to run — that's this script's job.
#
# Usage:
#   ./cursor/scripts/preflight.sh
#   ./cursor/scripts/preflight.sh --keep-going   # run all gates, report at end
#   ./cursor/scripts/preflight.sh --staged-only  # only lint-staged (fast check)

set -uo pipefail

KEEP_GOING=0
STAGED_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --keep-going) KEEP_GOING=1 ;;
    --staged-only) STAGED_ONLY=1 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "preflight: unknown arg: $arg" >&2
      exit 2
      ;;
  esac
done

# --- Detect runner ---------------------------------------------------------

if [ ! -f package.json ]; then
  echo "preflight: no package.json in $(pwd)" >&2
  exit 2
fi

PM=""
if [ -f pnpm-lock.yaml ]; then
  PM="pnpm"
elif [ -f yarn.lock ]; then
  PM="yarn"
elif [ -f package-lock.json ]; then
  PM="npm"
else
  # Fallback by command availability.
  for candidate in pnpm yarn npm; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PM="$candidate"
      break
    fi
  done
fi

if [ -z "$PM" ]; then
  echo "preflight: could not detect package manager (no lockfile, none on PATH)" >&2
  exit 2
fi

run_script() {
  # run_script <script-name>
  case "$PM" in
    pnpm) pnpm run "$1" ;;
    yarn) yarn run "$1" ;;
    npm)  npm run "$1" --silent ;;
  esac
}

has_script() {
  # has_script <script-name> -> 0 if present in package.json
  node -e "process.exit(require('./package.json').scripts && require('./package.json').scripts['$1'] ? 0 : 1)" 2>/dev/null
}

# --- Gate plan -------------------------------------------------------------

# Each gate: label|script-name (first existing script wins for aliases).
GATES=()

# pre-commit equivalent
if has_script "lint-staged"; then
  GATES+=("lint-staged|lint-staged")
fi

if [ "$STAGED_ONLY" -eq 1 ]; then
  : # skip the rest
else
  if has_script "lint"; then
    GATES+=("lint|lint")
  fi
  # typecheck: try common script names in order
  for ts_alias in compile-ts typecheck type-check tsc; do
    if has_script "$ts_alias"; then
      GATES+=("typecheck|$ts_alias")
      break
    fi
  done
  if has_script "test"; then
    GATES+=("test|test")
  fi
fi

if [ "${#GATES[@]}" -eq 0 ]; then
  echo "preflight: no recognized scripts in package.json (looking for lint-staged, lint, compile-ts/typecheck/tsc, test)"
  echo "preflight: nothing to run; treating as PASS"
  exit 0
fi

# --- Execute ---------------------------------------------------------------

echo "=== preflight: $PM, gates: ${#GATES[@]} ==="
FAILED=()
RAN=()

for gate in "${GATES[@]}"; do
  label="${gate%%|*}"
  script="${gate##*|}"
  echo ""
  echo "--- [$label] $PM run $script ---"
  if run_script "$script"; then
    RAN+=("$label:PASS")
  else
    rc=$?
    RAN+=("$label:FAIL($rc)")
    FAILED+=("$label")
    if [ "$KEEP_GOING" -eq 0 ]; then
      break
    fi
  fi
done

echo ""
echo "=== preflight summary ==="
for entry in "${RAN[@]}"; do
  echo "  - $entry"
done

if [ "${#FAILED[@]}" -gt 0 ]; then
  echo ""
  echo "preflight: FAIL (${FAILED[*]})"
  exit 1
fi

echo ""
echo "preflight: PASS"
exit 0
