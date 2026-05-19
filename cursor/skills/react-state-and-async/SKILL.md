---
name: react-state-and-async
description: State management and async patterns for React and React Native. Covers source-of-truth boundaries (server vs client vs URL vs form), cancellation, race conditions, optimistic updates, error models, selectors, reducers, and persistence/migration. Use when designing or reviewing state slices, sagas, queries, mutations, caching, async flows, or persistence shape changes. Stack-agnostic across Redux+Saga, RTK Query, React Query, Zustand, Jotai, or Context-only.
---

# React State & Async

## Source of truth — pick one per piece of data

| Kind | Owner | Examples |
|---|---|---|
| Server state | Server-state lib (RTK Query / React Query / saga + slice) | API responses, lists, entity caches |
| Client state (cross-screen) | Global store (Redux / Zustand / Jotai) | Auth, theme, feature flags |
| URL state (shareable) | URL search params / route params | Filters, sort, pagination, selected tab |
| Form state | Form library (RHF, Formik) or local | Draft inputs |
| Ephemeral UI | Local `useState` | Open menu, hover, focus |

**The most common bug**: server state copied into Redux without an invalidation strategy, then the two drift. Default to "server state stays in the server-state cache; selectors read from there." Only mirror into Redux when you have a concrete reason and document the sync.

## Cancellation

Every network call must be cancelable.

- **`fetch`** → `AbortController`. Cancel on unmount, on prop change, on new request.
- **Sagas** → `take` / `race` / `cancel`. Use `takeLatest` for "only the latest matters" flows; `takeEvery` for "every request matters" (e.g. analytics).
- **React Query** → cancellation is automatic via query keys; use `signal` in the query function.
- **RTK Query** → automatic via subscriber lifecycle; manual abort via `dispatch(api.endpoints.foo.initiate(arg)).abort()`.

If the agent finds a network call without a cancellation strategy, that's a bug.

## Race conditions

The pattern that keeps biting:

1. User changes filter → fetch A starts.
2. User changes filter again → fetch B starts.
3. A resolves after B → stale data wins.

Fixes:
- **`takeLatest`** in sagas.
- **Query keys** in React Query / RTK Query (the lib handles staleness).
- **`requestId` guard**: store the latest requestId, drop responses whose id ≠ latest.

## Optimistic updates

Default to **pessimistic**. Only go optimistic when:
- The action is a high-frequency UX (toggle, reorder).
- Failure is rare AND a rollback is straightforward.
- You can show clear failure feedback.

Optimistic without rollback is a bug. Always pair the optimistic patch with a `try/catch` that reverts the cache on error and surfaces a toast.

## Error model

Convert external errors at the boundary:

```ts
// inside saga or query function
try {
  return yield call(api.fetchUser, id);
} catch (e) {
  throw toDomainError(e); // -> typed UserNotFoundError | NetworkError | UnknownError
}
```

UI consumes typed errors and decides display. Never throw strings. Never let raw Axios errors leak into selectors/components.

## Selectors

- Memoize with `reselect` / `createSelector` for any selector that derives a new shape (filter, map, sort).
- Keep selectors pure; no side effects, no `Date.now()` inside.
- Selectors that take args: `createSelector` with input selectors that include the arg, or use `re-reselect` for memoized-per-arg.
- Don't return new object/array references on every call — that's the #1 cause of unnecessary re-renders.

## Reducers / slices

- Pure. Never mutate (Immer in RTK is fine — it produces immutable output).
- One slice per concern; resist the urge to make one mega-slice.
- `extraReducers` for cross-slice events (e.g. `auth/logout`).
- Selectors live next to the slice, not inside components.

## Side effects

- **Sagas** for complex orchestration: cancellation, debouncing, polling, sequencing.
- **RTK Query / React Query** for "fetch this and cache it" — 80% of cases.
- **Custom hooks** for one-off effects local to a feature.
- **Never** put effects in reducers/selectors.

## Persistence

When persisting state to MMKV / AsyncStorage / localStorage:

- **Version the shape**. Add a `__v` field; on read, run a migration if `__v` is older.
- **Persist only what survives a restart meaningfully**: auth tokens, user prefs, drafts. **Don't persist** ephemeral UI, server-state caches (re-fetch on launch), or anything sensitive without encryption (use Keychain/Keystore for secrets).
- **Hydrate before render**: app should not flash uninitialized state. Show a splash until hydrated.
- **Migration tests**: every shape change ships a migration test with a fixture of the old shape.

## Quick checklist

- [ ] Each piece of state has a single, declared owner (server / client / URL / form / local).
- [ ] No accidental duplication of server state into the client store.
- [ ] Every network call has a cancellation strategy.
- [ ] Concurrent flows handle staleness (`takeLatest`, query keys, or `requestId`).
- [ ] Optimistic updates always pair with a rollback.
- [ ] Errors are converted to domain types at the boundary.
- [ ] Selectors are memoized; no new references per call.
- [ ] Persistence shape is versioned with a migration on read.
- [ ] No effects inside reducers/selectors.
