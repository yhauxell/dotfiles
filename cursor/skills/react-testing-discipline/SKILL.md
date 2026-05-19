---
name: react-testing-discipline
description: Testing patterns for React and React Native. Covers behavior-over-implementation testing with React Testing Library / RN Testing Library, redux-saga-test-plan for sagas, snapshot policy, mocking at boundaries, async testing with `findBy*`, fake timers vs real timers, coverage focus, and common test anti-patterns. Use when designing the test layer for a new feature, writing tests for components or sagas, reviewing tests in a PR, or evaluating coverage of error paths and critical flows.
---

# React Testing Discipline

A test that breaks every time the code is refactored is worse than no test. A test that asserts behavior survives refactors and catches real regressions.

## Test what the user sees

### Component tests (RTL / RN Testing Library)
- **Query priority**: `getByRole` > `getByLabelText` > `getByText` > `getByTestId`. `getByTestId` is a last resort, not a default.
- Assert on **observable output**: rendered text, ARIA state, accessibility role, image alt text.
- **Don't assert on**: internal `useState` values, prop names, component class names, instance methods.

### Async assertions
- Use `findBy*` (returns a Promise) for elements that appear asynchronously.
- Use `waitFor` for assertions that need to settle.
- Never `setTimeout` inside a test to "wait for the network".
- `act` warnings are real — fix them; don't silence them.

### Anti-patterns
- `getByTestId('submit-button')` when a `getByRole('button', { name: /submit/i })` would work.
- Asserting on internal Redux action types from a component test.
- Re-rendering the entire app for a unit test of a single component.

## Sagas (redux-saga-test-plan)

Test:
- **Happy path**: action → effects → resulting state.
- **Cancellation**: a competing action / `take` cancels the in-flight saga.
- **Error path**: API throws → error action / state.
- **Race**: two concurrent triggers; assert only the latest wins.

Use `expectSaga(saga).provide(...)` to mock effects (`call`, `select`); avoid mocking the saga itself.

## Mocks: at the boundary, not the middle

- **Mock**: HTTP client (`axios`, `fetch`, RTK Query base query), native modules, time/random.
- **Don't mock**: your own sagas, selectors, or reducers under test. If you have to, the test is at the wrong layer.
- Reset all mocks between tests (`afterEach(() => jest.clearAllMocks())`).
- For HTTP, prefer **MSW** (Mock Service Worker) over per-call mocks — closer to real behavior and survives refactors.

## Snapshot tests

- **Allowed**: tiny presentational components that change rarely (a button, a badge, an icon).
- **Forbidden**: full screens, anything with a list, anything that branches on data.
- A snapshot that changes on every PR is noise; if the team blindly accepts updates, it's worse than no test.

## Timers

- **Real timers by default** (RN testing requires this for some libs).
- **Fake timers** (`jest.useFakeTimers()`) only when:
  - The test specifically needs deterministic time (debounce, polling).
  - You always restore real timers in `afterEach`.

## Coverage

- Target: **critical paths and error handling**, not a percentage number.
- **Branch coverage** matters more than line coverage — every `if`, every `?:`, every `?.`.
- For a new feature, the architect's SPEC lists the exact cases that must be covered. Treat that list as the contract.

## Test data

- Use **factories / fixtures** for complex objects, not inline literals scattered everywhere.
- Realistic data: real-looking IDs, real-looking dates, plausible text. `'foo'` everywhere makes tests harder to read.
- Mock data should mirror production shape — same components, same prop names, same value ranges.

## E2E (Detox / Maestro / Playwright / Cypress)

- Cover **critical user flows**, not every screen.
- Stable selectors: `accessibilityLabel` (RN) / `data-testid` (web).
- Wait for state with `waitFor` / explicit assertions, not `sleep`.
- Run on CI with retries — flaky E2E is a known cost; the answer is to fix the test, not to disable it.

## Anti-patterns to flag in review

- A test that calls `setState` directly to drive the component.
- A test that asserts on Redux action sequences for a presentational component.
- A test that re-implements business logic in the assertion (`expect(result).toBe(price * 1.21 + 5)`).
- "Coverage was added" that exercises code without asserting on its outputs.
- A snapshot file checked in for a component with dynamic content.
- `describe.only` / `it.only` / `xit` slipping into a PR.

## Quick checklist

- [ ] Tests query by role/label/text first, testId last.
- [ ] Async tested with `findBy*` / `waitFor`, not `setTimeout`.
- [ ] No `act()` warnings ignored.
- [ ] Mocks at the network boundary; sagas tested with redux-saga-test-plan.
- [ ] No snapshot tests for screens or branchy components.
- [ ] Real timers by default; fake only when needed.
- [ ] Critical paths and error handling covered; SPEC's required cases addressed.
- [ ] Test data via factories/fixtures, realistic shapes.
- [ ] No `.only` / `.skip` left in the diff.
