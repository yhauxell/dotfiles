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
#   ~/.claude/scripts/preflight.sh
#   ~/.claude/scripts/preflight.sh --keep-going    # run all gates, report at end
#   ~/.claude/scripts/preflight.sh --staged-only   # only lint-staged (fast check)
#
# Two-tier checks:
#   --affected[=<base-ref>]   Inner-loop fast path: lint + unit tests run ONLY on
#                             files changed vs the base ref (default: merge-base
#                             with origin/main|master, else HEAD~1). Typecheck
#                             still runs FULL (tsc is whole-program). NOT
#                             authoritative — run a full pass before merge/ship.
#   --base=<ref>              Override the diff base used by --affected.
#   --shard=<i/N>             Jest-native sharding for the test gate (e.g. 1/3),
#                             usable in full or --affected mode.
#
# Affected mode is for speed while iterating; the FULL run (no --affected) is the
# authoritative pre-merge / ship gate, because --findRelatedTests misses
# transitive breakage. The pipeline-orchestrator uses --affected during the
# implement loop and the full run at the ship gate.

set -uo pipefail

KEEP_GOING=0
STAGED_ONLY=0
AFFECTED=0
BASE_REF=""
SHARD=""
for arg in "$@"; do
  case "$arg" in
    --keep-going) KEEP_GOING=1 ;;
    --staged-only) STAGED_ONLY=1 ;;
    --affected) AFFECTED=1 ;;
    --affected=*) AFFECTED=1; BASE_REF="${arg#*=}" ;;
    --base=*) BASE_REF="${arg#*=}" ;;
    --shard=*) SHARD="${arg#*=}" ;;   # e.g. --shard=1/3 (jest-native)
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

run_script_with_args() {
  # run_script_with_args <script-name> -- <extra args...>
  local script="$1"; shift
  case "$PM" in
    pnpm) pnpm run "$script" -- "$@" ;;
    yarn) yarn run "$script" "$@" ;;
    npm)  npm run "$script" --silent -- "$@" ;;
  esac
}

pm_exec() {
  # pm_exec <binary> [args...] -> run a node_modules/.bin binary
  case "$PM" in
    pnpm) pnpm exec "$@" ;;
    yarn) yarn "$@" ;;
    npm)  npx --no-install "$@" ;;
  esac
}

resolve_base_ref() {
  # Echo the base ref to diff against. Prefer the user-provided ref, else the
  # merge-base with the upstream default branch, else HEAD~1.
  if [ -n "$BASE_REF" ]; then echo "$BASE_REF"; return; fi
  for b in origin/main origin/master main master; do
    if git rev-parse --verify --quiet "$b" >/dev/null 2>&1; then
      git merge-base HEAD "$b" 2>/dev/null && return
    fi
  done
  echo "HEAD~1"
}

changed_source_files() {
  # Print added/copied/modified TS/JS source files vs the base ref, excluding
  # generated/lock/snapshot noise. NUL-safe enough for typical paths.
  local base; base="$(resolve_base_ref)"
  {
    git diff --name-only --diff-filter=ACM "$base"...HEAD 2>/dev/null
    git diff --name-only --diff-filter=ACM 2>/dev/null            # unstaged
    git diff --name-only --diff-filter=ACM --cached 2>/dev/null   # staged
  } | sort -u \
    | grep -E '\.(ts|tsx|js|jsx)$' \
    | grep -vE '(^|/)(node_modules|dist|build|coverage)/' \
    | grep -vE '\.(snap)$' \
    | grep -vE '(ampli|__generated__|\.gen\.)' || true
}

# --- Affected mode (inner-loop fast path) ----------------------------------
# lint + unit tests run only on files affected by the branch diff; typecheck
# ALWAYS runs full because tsc is whole-program (a one-line type change can
# break distant consumers). Affected mode is for iteration speed — the FULL
# run (default mode) remains the authoritative pre-merge / ship gate.

if [ "$AFFECTED" -eq 1 ]; then
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "preflight: --affected requires a git repo; falling back to full run" >&2
    AFFECTED=0
  fi
fi

if [ "$AFFECTED" -eq 1 ]; then
  BASE="$(resolve_base_ref)"
  # Read changed files into an array (newline-delimited).
  FILES=()
  while IFS= read -r line; do [ -n "$line" ] && FILES+=("$line"); done < <(changed_source_files)

  echo "=== preflight: AFFECTED mode ($PM, base=$BASE, ${#FILES[@]} changed source files) ==="
  if [ "${#FILES[@]}" -gt 0 ]; then
    printf '  - %s\n' "${FILES[@]}"
  fi

  AFF_RAN=()
  AFF_FAILED=()

  # 1) lint — changed files only
  if [ "${#FILES[@]}" -eq 0 ]; then
    AFF_RAN+=("lint:SKIP(no files)")
  else
    echo ""; echo "--- [lint] eslint (changed files) ---"
    if pm_exec eslint "${FILES[@]}"; then AFF_RAN+=("lint:PASS"); else AFF_RAN+=("lint:FAIL"); AFF_FAILED+=("lint"); fi
  fi

  # 2) typecheck — ALWAYS full (tsc is whole-program)
  TS_SCRIPT=""
  for ts_alias in compile-ts typecheck type-check tsc; do
    if has_script "$ts_alias"; then TS_SCRIPT="$ts_alias"; break; fi
  done
  if [ -n "$TS_SCRIPT" ]; then
    echo ""; echo "--- [typecheck] $PM run $TS_SCRIPT (FULL — tsc is whole-program) ---"
    if run_script "$TS_SCRIPT"; then AFF_RAN+=("typecheck:PASS"); else AFF_RAN+=("typecheck:FAIL"); AFF_FAILED+=("typecheck"); fi
  else
    AFF_RAN+=("typecheck:SKIP(no script)")
  fi

  # 3) test — only tests related to the changed files
  if has_script "test"; then
    JEST_ARGS=(--watchAll=false --passWithNoTests --maxWorkers=50%)
    [ -n "$SHARD" ] && JEST_ARGS+=("--shard=$SHARD")
    if [ "${#FILES[@]}" -gt 0 ]; then
      JEST_ARGS+=(--findRelatedTests "${FILES[@]}")
    fi
    echo ""; echo "--- [test] $PM run test ${JEST_ARGS[*]} ---"
    if run_script_with_args test "${JEST_ARGS[@]}"; then AFF_RAN+=("test:PASS"); else AFF_RAN+=("test:FAIL"); AFF_FAILED+=("test"); fi
  else
    AFF_RAN+=("test:SKIP(no script)")
  fi

  echo ""; echo "=== preflight summary (AFFECTED) ==="
  for entry in "${AFF_RAN[@]}"; do echo "  - $entry"; done
  if [ "${#AFF_FAILED[@]}" -gt 0 ]; then
    echo ""; echo "preflight: FAIL (${AFF_FAILED[*]})"
    echo "preflight: NOTE — affected mode is not authoritative; run a full \`preflight.sh\` before merge."
    exit 1
  fi
  echo ""
  echo "preflight: PASS (affected) — run full \`preflight.sh\` before merge/ship."
  exit 0
fi

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
  # Full-mode sharding: pass --shard / --maxWorkers through to the test gate only.
  if [ "$label" = "test" ] && [ -n "$SHARD" ]; then
    echo "--- [$label] $PM run $script --shard=$SHARD --maxWorkers=50% ---"
    if run_script_with_args "$script" "--shard=$SHARD" "--maxWorkers=50%" "--watchAll=false"; then
      RAN+=("$label:PASS"); continue
    else
      rc=$?; RAN+=("$label:FAIL($rc)"); FAILED+=("$label")
      [ "$KEEP_GOING" -eq 0 ] && break || continue
    fi
  fi
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
