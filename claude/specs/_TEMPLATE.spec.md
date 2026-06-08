---
# Global SPEC template (user-level). Do not edit in place when used as a template.
# The architect copies this structure into the active project's
#   .cursor/specs/<feature-slug>.spec.md
# (kebab-case, ticket key prefix preferred,
# e.g. PROJ-123-add-user-profile-page.spec.md).
#
# A project may override this template by creating its own .cursor/specs/_TEMPLATE.spec.md;
# when present, the project-local template wins.
#
# Append-only convention (mirrors ~/.cursor/AGENTS.md):
#   - Never overwrite an existing spec.
#   - On material change, bump `version` AND filename suffix (`.spec.v2.md`, `.spec.v3.md`).
#   - Older versions remain as historical record.
---

# <Feature title>

## Meta
- ticket: <TICKET-KEY, e.g. PROJ-123>
- author_agent: frontend-architect
- design_source: <Figma URL or "n/a">
- depends_on_spec: <previous spec filename or "n/a">
- status: draft | approved | implementing | shipped
- version: 1
- created: <YYYY-MM-DD>
- updated: <YYYY-MM-DD>

## 1. Intent (the "why")
One short paragraph. What user/business outcome does this change produce?
Anti-goal: do not restate the ticket; explain the *why* in product terms.

## 2. Scope
### In scope
- bullet 1
- bullet 2

### Out of scope (non-goals)
- bullet 1
- bullet 2

## 3. Constraints & non-functional requirements
- Compatibility: <mobile release / backend version / persisted-state version>
- Performance budget: <render budget, bundle delta, request waterfall>
- Accessibility: <roles, focus, touch targets, screen reader path>
- Security: <auth gate, PII boundary, sanitization>
- Telemetry: <events, GA flow, error tracking>
- Feature flag: <LD flag name or "none">

## 4. Design context (from figma-design-implementer, if any)
Paste the verbatim `## Design context (handoff to frontend-architect)` block here, or
write `n/a` if the change has no Figma source. The block stays unmodified; the architect
folds it into sections 5–9 below.

## 5. Pattern donors
List existing files/components/sagas in this codebase that this feature should mirror or
extend, so the implementer reuses patterns instead of inventing new ones.
- `src/...` — why it's the donor
- `src/...` — why it's the donor

## 6. Component tree
Tree of components/screens introduced or modified, with ownership of state.
```
<RoutePage>
  <FeatureContainer>     // owns: form state, submit lifecycle
    <FeatureView>        // pure presentational
      <SubcomponentA />
      <SubcomponentB />
```

## 7. Contracts (single source of truth)
### TypeScript types
```ts
// New / changed exported types live here.
// These are authoritative — implementer must match exactly.
```

### API / route shapes
- `POST /v1/foo` request: `{...}` response: `{...}` errors: `{...}`
- Route: `/foo/:id` params: `{...}` query: `{...}`

### Redux / state shape
```ts
// New slice, selectors, action creators, saga signatures.
```

## 8. File manifest
Every file that will be created or modified. Implementer must not edit files outside this
list without amending the spec.
- [ ] `src/pages/Foo/FooContainer.tsx` (new)
- [ ] `src/pages/Foo/FooContainer.test.tsx` (new)
- [ ] `src/store/foo/fooSaga.ts` (modify)
- [ ] `src/api/foo.ts` (new)

## 8.5 PR plan
How this work is split for human review. Triggered when the change touches **>~10 hand-written source files** (exclude lockfiles/generated/snapshots) **OR** spans **≥2 review layers** `{ui, state, api-integration, observability, analytics}`. If neither trigger fires, write `_Single PR — change is small and single-layer._`.

Rules: default to a horizontal layer split in merge order (`api-integration → state → ui`, then `observability`/`analytics`); override to vertical thin slices when layers are too coupled to review independently. **Tests ship in their layer's PR — never a separate "tests" PR.** Each PR must independently pass `/preflight` (full) and be independently revertible. Declare merge order and stacked-branch dependencies.

| PR | Layer(s) | Files (subset of §8) | Base branch | Depends on | Acceptance |
|----|----------|----------------------|-------------|------------|------------|
| PR1 | api-integration | `src/api/foo.ts` + tests | `main` | — | preflight PASS |
| PR2 | state | slice/saga + tests + store wiring | PR1 (stacked) | PR1 | preflight PASS |
| PR3 | ui | screen/components + tests | PR2 (stacked) | PR2 | preflight PASS |

- **Split mode**: horizontal | vertical — why: <one line>
- **Merge order**: <explicit>

## 9. Tasks (atomic, ordered, verifiable)
Each task must be small enough to ship in isolation if forced to.
The implementer (manual or future `feature-implementer` subagent) runs them top-to-bottom
and executes `verify_commands` between tasks.

### T1 — <short imperative name>
- depends_on: []
- files: [`src/api/foo.ts`]
- action: |
    Add the typed API client function for `POST /v1/foo`. Follow the donor pattern in
    `src/api/bar.ts`. Use the Axios wrapper at `src/api/client.ts` — do not use `fetch`.
- acceptance:
    - Function signature matches the contract in §7.
    - Errors are mapped to domain errors at the boundary (per typescript-coding-standards rule).
- verify_commands:
    - `yarn compile-ts`
    - `yarn lint src/api/foo.ts`

### T2 — <next task>
- depends_on: [T1]
- files: [`src/store/foo/fooSaga.ts`]
- action: |
    ...
- acceptance:
    - ...
- verify_commands:
    - `yarn test src/store/foo`

### T_last — Wire telemetry & feature flag
- depends_on: [T_prev]
- files: [...]
- action: |
    ...
- acceptance:
    - GA events fire per §3 telemetry.
    - Feature is gated by the LD flag from §3.
- verify_commands:
    - `yarn lint && yarn compile-ts && yarn test`

## 10. Decisions & rejected alternatives
For each non-obvious decision, record:
- **D1:** <decision>
  - chosen: <option>
  - rejected: <option> — because <reason>
  - tradeoff: <what we give up>

## 11. Open questions
Numbered. Each must be answered before status moves from `draft` → `approved`.
1. ...
2. ...

## 12. Test strategy
Mapped to `react-testing-discipline` + `.cursor/rules/test-standards.mdc`.
- Unit: <what>
- Saga (redux-saga-test-plan): <what>
- Integration (RTL): <what>
- E2E (Playwright): <what or "n/a">
- Manual QA: produced by `manual-test-planner` post-implementation; lives at
  `docs/test-plans/<branch-slug>.md`.

## 13. Rollout & cleanup
- Rollout: <feature flag plan, % ramp, monitoring>
- Cleanup ticket: <TICKET-KEY> (filed when the flag will be removed)
- Cleanup doc lives at `docs/cleanup/<branch-slug>.md` when applicable.

## Change log
- v1 (<YYYY-MM-DD>): initial spec.
