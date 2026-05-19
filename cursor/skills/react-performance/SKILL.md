---
name: react-performance
description: Performance patterns for React and React Native. Covers memoization (React.memo, useMemo, useCallback), list virtualization, code splitting, bundle hygiene, render budgets, concurrent rendering (Suspense, startTransition), and avoiding request waterfalls. Use when designing or reviewing performance-sensitive surfaces, large lists, frequently-rendered components, or when a feature touches bundle size, render counts, or animation smoothness.
---

# React Performance

Performance work has three goals: **fewer renders**, **cheaper renders**, **smaller bundles**. Optimize in that order.

## Memoization — when it pays, when it's noise

### When `React.memo` helps
- **Leaf components rendered in lists** (FlatList rows, table cells, grid cells).
- **Heavy presentational components** with many primitive props.
- **Children of frequently-re-rendering parents** where the children's props rarely change.

### When `React.memo` is wasted
- Components that receive **new objects/arrays/functions every render** (memo gets defeated by inline `{}` / `() => {}` / `[]`).
- Components that render fast and are mounted once.
- Components that read context (memo can't stop context-driven re-renders).

### `useMemo` / `useCallback`
- **`useCallback`** for stable references passed to memoized children or to dependency arrays.
- **`useMemo`** for expensive derivations (sorting, filtering, parsing) and for stable object references in props.
- **Don't `useMemo` cheap calculations** — the hashing cost outweighs the work.

### Stable references checklist
- [ ] Inline `{}` / `[]` / `() => {}` props going into `React.memo`'d children → wrap in `useMemo` / `useCallback`.
- [ ] Context provider `value` is `useMemo`'d.
- [ ] Selectors return stable references via `createSelector`.

## Lists & virtualization

### React Native
See `react-native-architecture` skill. Short version: `FlatList` / `SectionList` for >20 items; memoized `renderItem`; `keyExtractor`; `getItemLayout` when applicable.

### Web SPA
- **>50 items rendered at once → virtualize.** Libraries: `@tanstack/react-virtual`, `react-window`, `react-virtuoso`.
- Pagination / infinite scroll when virtualization is overkill.
- Avoid `.map()` rendering 1000s of DOM nodes; the browser will not save you.

### Anti-patterns
- Sorting/filtering inside `render` over a 10K-item array.
- `key={index}` on items that can reorder.
- Images without dimensions in lists → constant layout thrash.

## Code splitting

- **Route-level splits** with `React.lazy` + `Suspense` (web) or RN `require` on demand.
- **Heavy dialog/modal content** that is rarely opened: split it.
- **Don't over-split**: every chunk is a request; lazy-loading a button is a regression.
- Provide a fallback that matches the layout (skeleton over spinner).

## Bundle hygiene

- Always use **submodule imports** when the lib supports it:
  - `import debounce from 'lodash/debounce'` — not `import { debounce } from 'lodash'`.
  - `import { format } from 'date-fns'` — already tree-shakeable; avoid `moment` (huge, mutable).
- One date library. One HTTP client. One state lib (or a clear migration plan).
- Audit largest deps with `vite-bundle-visualizer` / `webpack-bundle-analyzer` / `source-map-explorer` before opinions.
- Polyfill only what you actually need (`core-js` per-feature, not the kitchen sink).

## Concurrent rendering (React 18+)

- **`Suspense`** for async UI: data fetching libraries that support it (Relay, RTK Query w/ `useSuspenseQuery`, React Query w/ `useSuspenseQuery`) automatically suspend; show a skeleton at the boundary.
- **`startTransition`** for state updates that don't need to be urgent (typing into a search box that filters a heavy list).
- **`useDeferredValue`** for computed values that lag behind input on slow devices.

Don't sprinkle these everywhere. Each Suspense boundary is a UX decision; default to one per route.

## Render-count discipline

- Use the **React DevTools Profiler** (web) or **Performance Monitor** (RN) to verify before optimizing. Premature memo is technical debt.
- Aim for **<16ms render** on the most-rendered components on a target device (mid-range Android, not a developer laptop).
- A common offender: a context whose `value` is recreated every render and whose consumers are large trees. Fix by memoizing the value or splitting the context.

## Network waterfalls

- Identify with the Network panel: are independent requests serialized?
- **Parallelize** with `Promise.all`, multiple `useQuery` calls, or saga `all`.
- **Prefetch** on hover, on route entry, on idle (`requestIdleCallback`).
- Avoid the "fetch in parent, then fetch in child" pattern unless the child genuinely depends on the parent's result.

## Animation budget

- Animations targeting **60 fps** must finish their work in <16.6ms per frame.
- On RN, run animations on the UI thread (Reanimated worklets). On web, prefer CSS transitions / `transform` / `opacity` over JS-driven layout changes.
- Avoid animating `width` / `height` / `top` / `left` when `transform: translate / scale` would do.

## Quick checklist

- [ ] Inline `{}` / `[]` / `() => {}` props are not landing in `React.memo`'d children.
- [ ] Context providers `useMemo` their `value`.
- [ ] Selectors are memoized; lists are virtualized.
- [ ] Route-level code splits exist; non-critical heavy modals are split.
- [ ] Submodule imports for `lodash`, `date-fns`, etc.
- [ ] One date lib, one HTTP client.
- [ ] Suspense boundaries placed deliberately (typically per route).
- [ ] Animations are GPU-accelerated (transform/opacity) or run on the UI thread (RN worklets).
- [ ] Profiled before claiming a perf win; numbers attached.
