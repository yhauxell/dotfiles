---
description: Declare the change_class (trivial | feature | epic) up front. Per CLAUDE.md §0, this is the most important decision in the pipeline — it determines how much process the change gets.
argument-hint: <one-line description of the work>
---

Per `CLAUDE.md` §0, classify the work described below into exactly one of `trivial`, `feature`, or `epic`. Be honest — default to the lightest class that fits.

**Heuristics**:

- `trivial` → one file, no new user-visible behavior. Copy tweaks, typo fixes, dep bumps, single-icon swaps, comment changes.
- `feature` → new user-visible flow OR change touches ≥2 of {component, store, api, route} OR non-trivial state/async work.
- `epic` → multi-feature or multi-week. Crosses module boundaries. Multiple SPECs likely. Worth tracking state across sessions.

**Work to classify**:

$ARGUMENTS

**Your output**:

1. **Class**: `trivial` | `feature` | `epic` — one word.
2. **Reasoning**: 2–3 sentences citing the heuristic that decided it.
3. **Next steps** for this class:
   - `trivial` → edit directly, then `/preflight` before commit.
   - `feature` → apply `ticket-refinement` skill if there's a ticket, then `/architect` → `/implement` → `/review` → `/preflight` (or `/ship`).
   - `epic` → `/epic-start <slug>` to begin.

If on the fence between `trivial` and `feature`, pick `feature`. If on the fence between `feature` and `epic`, pick `feature` — escalating to `epic` later is cheap; over-classifying upfront is wasteful.
