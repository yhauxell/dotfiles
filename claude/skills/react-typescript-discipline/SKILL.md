---
name: react-typescript-discipline
description: TypeScript discipline for React and React Native. Covers the type-assertion hierarchy (inference > satisfies > predicates > narrow as > as unknown as T), the ban on `as any`, discriminated unions for state machines, branded types for IDs, runtime validation at boundaries (Zod), domain error types, and module/import conventions. Use when authoring or reviewing TypeScript in a React/RN codebase, when resolving any/`as` escape hatches, when designing slice/state shapes, or when a public API surface needs typed contracts.
---

# React TypeScript Discipline

The point of TS is to catch bugs at compile time. Every escape hatch (`as any`, `as unknown as T`, `@ts-ignore`) is a hole in that net.

## Assertion hierarchy

Prefer in order:

1. **Type inference** — let TS infer.
2. **Type annotation** — `const x: Type = ...`.
3. **Type predicate** — `function isFoo(v: unknown): v is Foo`.
4. **`satisfies`** — validate shape without widening.
5. **`as const`** — for literal types and readonly.
6. **Narrow `as Type`** — only after a runtime guard, scoped tightly.
7. **`as unknown as T`** — last resort, with comment + ticket reference.

## Forbidden

- **`as any`** — banned. Disables all checking; hides bugs. The only acceptable uses are:
  - Documented temporary workaround with a `// TODO:` and ticket.
  - Third-party library bug with a link to upstream.
  - Truly impossible generic constraint (extremely rare).
- **`@ts-ignore`** — prefer `@ts-expect-error` so the comment fails when the underlying issue is fixed.
- **`as unknown as T`** without justification — every occurrence needs a comment explaining the runtime guarantee.

## Discriminated unions for state

```ts
type RequestState<T, E = DomainError> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: E };
```

Then narrow by `status`:

```ts
function render(state: RequestState<User>) {
  switch (state.status) {
    case 'idle':    return <Idle />;
    case 'loading': return <Spinner />;
    case 'success': return <UserView user={state.data} />;
    case 'error':   return <Error error={state.error} />;
    default: {
      const _exhaustive: never = state;
      return _exhaustive;
    }
  }
}
```

The `never` assertion catches missing cases when a new state is added.

## Branded types for IDs

Prevent accidental mixing of ID types:

```ts
type UserId    = string & { readonly __brand: 'UserId' };
type ProductId = string & { readonly __brand: 'ProductId' };

function asUserId(s: string): UserId { return s as UserId; }
```

Now `getUser(productId)` is a compile error.

## `satisfies` for config

```ts
const config = {
  apiUrl: 'https://api.example.com',
  timeout: 5000,
  retries: 3,
} satisfies AppConfig;
// `config.apiUrl` is `'https://api.example.com'`, not `string`
```

Validates shape without widening literal types.

## Runtime validation at boundaries

Untrusted input (HTTP responses, deep links, persisted storage) is `unknown`. Validate with **Zod** (or similar), then assert once:

```ts
import { z } from 'zod';

const UserSchema = z.object({
  id: z.string(),
  email: z.string().email(),
});

export function parseUser(data: unknown): User {
  return UserSchema.parse(data); // throws on invalid; returns typed User
}
```

After `parse`, the result is fully typed. No `as` needed.

## Errors

- Throw `Error` (or domain error subclasses), never strings.
- Convert external errors at the boundary (saga / query function), not in components:

```ts
class UserNotFoundError extends Error { constructor(id: UserId) { super(`User ${id} not found`); } }
class NetworkError extends Error {}
type DomainError = UserNotFoundError | NetworkError;
```

Selectors and components consume `DomainError`, not raw Axios errors.

## Public API of a feature module

A feature folder should have a single barrel (`index.ts`) that re-exports the **public** surface:

```ts
// src/features/users/index.ts
export { UserScreen } from './UserScreen';
export { useUser } from './hooks/useUser';
export { selectUserById } from './selectors';
export type { User, UserId } from './types';
```

Anything not re-exported is private to the feature. Never import from another feature's internal files.

## React-specific TS patterns

### Component props
```ts
type ButtonProps = {
  intent?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  onPress: () => void;
  children: React.ReactNode;
};

export function Button({ intent = 'primary', size = 'md', onPress, children }: ButtonProps) { ... }
```

- Prefer `type` for props; `interface` for extendable contracts.
- Avoid `React.FC` — implicit `children`, awkward generics. Use plain function with typed props.

### Hooks
- Return tuples or objects with explicit return types when the inference is unclear:
```ts
export function useToggle(initial = false): readonly [boolean, () => void] {
  ...
}
```
- For polymorphic hooks, generic constraints over conditional types:
```ts
export function useQueryParam<T extends string>(key: T): string | null { ... }
```

### Refs
- `useRef<HTMLDivElement>(null)` for DOM refs (web).
- `useRef<View>(null)` for RN refs.
- Imperative handles via `forwardRef` + `useImperativeHandle` only when truly needed.

## Modules & imports

- **Named exports**, not default — better refactor support.
- No cyclic dependencies; if you find one, extract shared types/utilities into a third file.
- Path aliases (`@/features/...`) configured in `tsconfig` and matching ESLint resolver.

## Strict config

- `"strict": true` (covers `noImplicitAny`, `strictNullChecks`, etc.).
- `"noUncheckedIndexedAccess": true` — array/dict access yields `T | undefined`. Painful at first, catches real bugs.
- `"exactOptionalPropertyTypes": true` — distinguishes `{ x?: T }` from `{ x: T | undefined }`.

## Quick checklist

- [ ] No `as any` (or it has a comment + ticket).
- [ ] No `@ts-ignore` (use `@ts-expect-error`).
- [ ] Discriminated unions for request states; `never` exhaustiveness on switches.
- [ ] Branded types for IDs that flow across modules.
- [ ] `satisfies` for config / fixture objects.
- [ ] Untrusted input validated at the boundary; no `as Type` on raw `unknown`.
- [ ] Errors are typed; no string throws.
- [ ] Feature module has a barrel; no cross-feature internal imports.
- [ ] `strict` is on; new code does not introduce `any` regressions.
