---
name: react-spa-architecture
description: Patterns and pitfalls for client-side React Single-Page Applications (Vite, CRA, Webpack with React Router or TanStack Router). Covers routing, code splitting, error boundaries, URL-as-state, route-level auth gating, and SPA-specific anti-patterns. Use when designing or reviewing a feature in a client-rendered React app with no SSR/RSC. Also use when stack detection identifies a React SPA (no `next.config`, no server components).
---

# React SPA Architecture

Client-side React only. **No SSR. No RSC. No `use client` directives.** If the codebase is server-rendered, this skill does not apply — flag and stop.

## Routing

### Default stack
- **React Router v6+** for most existing apps; **TanStack Router** for newer typed-route projects.
- Centralize route names/paths in a single module; import constants, never inline strings.
- Use **nested routes** with `<Outlet />` for shared layouts (header/sidebar) instead of duplicating chrome in every screen.

### Patterns
- **Route-level data**: load via the router's loader (TanStack) or via the page component on mount with cleanup, not in `App.tsx`.
- **Auth/permission gating**: a single `<ProtectedRoute>` wrapper or route guard, not scattered conditionals inside screens.
- **404 boundary**: explicit catch-all route at the end of the route tree.
- **URL-as-state**: filters, sort, pagination → `useSearchParams`. Do not duplicate URL state into Redux unless multiple routes consume it; if duplicated, document the sync direction.
- **Programmatic navigation**: `useNavigate` only inside event handlers / effects, never inside the render body.

### Anti-patterns
- `useNavigate()` called during render → causes warnings and double navigations.
- Missing `<Outlet />` in a layout route → child routes silently render nothing.
- Unguarded routes that read auth state inside the screen instead of at the route boundary.
- A global "current route" string maintained in Redux that drifts from `useLocation()`.
- Route component imported eagerly when it could be lazy.

## Code splitting

### Defaults
- **Split at route boundaries** with `React.lazy` + `<Suspense>`. Each top-level route gets its own chunk.
- **Do not over-split**: lazy-loading every leaf component creates request waterfalls and worse UX.
- **Suspense fallback**: a route-level skeleton that matches the layout, not a generic spinner.

### When to split deeper than route level
- A heavy library used by only one tab/modal (e.g. a chart lib, a rich text editor).
- A diagnostic/admin panel rarely opened by users.

### Anti-patterns
- Lazy-loading the home/landing route (defeats fast first paint).
- Lazy-loading components inside a tight loop or list (one fetch per render).
- Missing `<Suspense>` boundary around a `React.lazy` component → app crashes.

## Error boundaries

- **Per route**: each route segment wraps its content in an `<ErrorBoundary>` so one screen's crash doesn't break the shell.
- **Global fallback**: a top-level boundary above the router for catastrophic errors.
- **Reset semantics**: pass a `resetKeys` (e.g. `[location.pathname]`) so navigating away clears the boundary.
- **Reporting**: forward to Sentry/error reporter inside `componentDidCatch` or via `react-error-boundary`'s `onError`.

## URL & state

| State kind | Source of truth | Example |
|---|---|---|
| Filters, sort, pagination | URL search params | `?sort=date&page=2` |
| Selected tab when shareable | URL | `/users/123?tab=billing` |
| Auth, current user | Global store | `state.auth.user` |
| Server data | Server-state lib (RTK Query / React Query) | `useGetUserQuery(id)` |
| Form drafts | Form library (RHF, Formik) | local to form |
| Ephemeral UI (open menu, hover) | Local component state | `useState` |

Do not blur these layers. The most common bug is "we put a filter in Redux and then forgot to sync the URL".

## Layout & shell

- **AppShell** (header, sidebar, footer) is rendered once via a layout route. Screens render inside `<Outlet />`.
- **Modals**: prefer a single modal portal at the app root, controlled by a small store (Zustand or context). Avoid mounting modals deep inside screens.
- **Toasts/notifications**: portal at app root, imperatively triggered.

## Bundling & imports

- Vite/CRA/Webpack will only tree-shake when you import submodules: `import debounce from 'lodash/debounce'`, not `import { debounce } from 'lodash'`.
- Prefer `date-fns` over `moment`; `dayjs` is also fine. Never ship both.
- Audit the largest deps with `vite-bundle-visualizer` / `webpack-bundle-analyzer` before declaring a perf decision.

## Hydration / SSR

- Not applicable. If you find `getServerSideProps`, `app/` directory with server components, or `renderToPipeableStream`, this is not an SPA. Stop and flag the stack mismatch.

## Quick checklist

- [ ] Route table centralized; no string-literal navigation.
- [ ] Layout route(s) with `<Outlet />`; no chrome duplication.
- [ ] Auth gating at the route boundary, not scattered in screens.
- [ ] 404 catch-all present.
- [ ] Top-level routes are `React.lazy`'d with a route-shaped fallback.
- [ ] Per-route error boundary; navigation resets it.
- [ ] URL holds shareable state (filters/sort/tab); duplications are intentional and documented.
- [ ] Submodule imports for `lodash`/`date-fns` etc.
- [ ] No SSR/RSC artifacts in the codebase.
