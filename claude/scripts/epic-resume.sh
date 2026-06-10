#!/usr/bin/env bash
# epic-resume.sh — headless resume trigger for autopilot epics.
#
# Scans <project>/.claude/pipeline/*.state.yaml and, for each epic that is
# safe to advance, runs:
#   claude -p "/epic-continue <slug>" --permission-mode acceptEdits
# from the project root. Designed to be invoked by cron, launchd, or a
# scheduled agent — it is idempotent and locks per slug.
#
# An epic is resumed only when ALL of the following hold
# (see claude/specs/full-automation.spec.md §7):
#   1. autopilot: true in the state YAML
#   2. stage is not a hard gate (spec_draft, pr_open) and not done
#   3. the repo's checked-out branch matches the epic's branch (clobber guard)
#   4. the per-slug lock is acquired (no concurrent resume)
#
# pr_open special case: if `gh pr view <pr_url>` reports the PR is MERGED,
# the human gate has cleared — the epic is resumed so the orchestrator can
# advance merged -> retro.
#
# Usage:
#   epic-resume.sh [--dry-run] <project-dir> [<project-dir> ...]
#
# Exit codes: 0 = all epics evaluated (resumed or skipped); 1 = usage /
# script-level error. Per-epic outcomes are appended to
# ~/.claude/logs/epic-resume.log.

set -u

LOG_DIR="$HOME/.claude/logs"
LOG_FILE="$LOG_DIR/epic-resume.log"
LOCK_DIR="$HOME/.claude/locks"
HARD_GATES="spec_draft"
TERMINAL="done"
DRY_RUN=0

usage() {
  grep '^#' "$0" | sed 's/^# \{0,1\}//' | sed -n '1,30p'
}

log() {
  local msg="[$(date '+%Y-%m-%dT%H:%M:%S%z')] $*"
  echo "$msg" >> "$LOG_FILE"
  echo "$msg"
}

# Naive single-key YAML extraction. State files are machine-written by the
# orchestrator, so top-level/nested "key: value" lines are reliable.
yaml_get() { # yaml_get <file> <key>
  sed -n "s/^[[:space:]]*$2:[[:space:]]*//p" "$1" | head -n 1 | tr -d '"' | tr -d "'"
}

resume_epic() { # resume_epic <project> <slug>
  local project="$1" slug="$2"
  if [ "$DRY_RUN" -eq 1 ]; then
    log "DRY-RUN $slug: would resume (claude -p \"/epic-continue $slug\" --permission-mode acceptEdits) in $project"
    return 0
  fi
  local lock="$LOCK_DIR/epic-resume.$slug.lock"
  if ! mkdir "$lock" 2>/dev/null; then
    log "SKIP $slug: lock held ($lock) — another resume is in flight"
    return 0
  fi
  # shellcheck disable=SC2064  # expand lock path now, not at trap time
  trap "rmdir '$lock' 2>/dev/null" RETURN
  log "RESUME $slug: stage advance in $project"
  ( cd "$project" && claude -p "/epic-continue $slug" --permission-mode acceptEdits ) \
    >> "$LOG_FILE" 2>&1
  local rc=$?
  rmdir "$lock" 2>/dev/null
  trap - RETURN
  if [ $rc -eq 0 ]; then
    log "OK $slug: claude run finished"
  else
    log "FAIL $slug: claude exited $rc (see log above)"
  fi
}

check_epic() { # check_epic <project> <state-file>
  local project="$1" state="$2"
  local slug stage autopilot branch pr_url current_branch
  slug=$(yaml_get "$state" slug)
  stage=$(yaml_get "$state" stage)
  autopilot=$(yaml_get "$state" autopilot)
  branch=$(yaml_get "$state" branch)
  pr_url=$(yaml_get "$state" pr_url)
  [ -n "$slug" ] || { log "SKIP $state: no slug"; return 0; }

  if [ "$autopilot" != "true" ]; then
    log "SKIP $slug: autopilot is off"
    return 0
  fi
  case " $TERMINAL " in *" $stage "*)
    log "SKIP $slug: terminal stage '$stage'"
    return 0;;
  esac
  case " $HARD_GATES " in *" $stage "*)
    log "SKIP $slug: hard gate '$stage' (needs /approve-spec)"
    return 0;;
  esac

  if [ "$stage" = "pr_open" ]; then
    # Human merge gate — only resume if the PR is already merged.
    if [ -z "$pr_url" ] || [ "$pr_url" = "null" ]; then
      log "SKIP $slug: stage pr_open but no pr_url recorded"
      return 0
    fi
    local pr_state
    pr_state=$(gh pr view "$pr_url" --json state -q .state 2>/dev/null)
    if [ "$pr_state" != "MERGED" ]; then
      log "SKIP $slug: hard gate pr_open — PR state is '${pr_state:-unknown}' (waiting for human merge)"
      return 0
    fi
    log "GATE-CLEARED $slug: PR merged — resuming to advance merged -> retro"
  fi

  current_branch=$(git -C "$project" rev-parse --abbrev-ref HEAD 2>/dev/null)
  if [ -n "$branch" ] && [ "$branch" != "null" ] && [ "$current_branch" != "$branch" ]; then
    log "SKIP $slug: checked-out branch '$current_branch' != epic branch '$branch' (clobber guard)"
    return 0
  fi

  resume_epic "$project" "$slug"
}

main() {
  [ $# -ge 1 ] || { usage; exit 1; }
  if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then usage; exit 0; fi
  if [ "$1" = "--dry-run" ]; then DRY_RUN=1; shift; fi
  [ $# -ge 1 ] || { usage; exit 1; }

  mkdir -p "$LOG_DIR" "$LOCK_DIR"

  local project state found=0
  for project in "$@"; do
    if [ ! -d "$project" ]; then
      log "ERROR: project dir not found: $project"
      continue
    fi
    project=$(cd "$project" && pwd)
    for state in "$project"/.claude/pipeline/*.state.yaml; do
      [ -e "$state" ] || continue
      case "$(basename "$state")" in _TEMPLATE*) continue;; esac
      found=1
      check_epic "$project" "$state"
    done
  done
  [ "$found" -eq 1 ] || log "no epic state files found under given projects"
}

main "$@"
