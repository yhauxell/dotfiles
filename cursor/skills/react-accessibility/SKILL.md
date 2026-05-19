---
name: react-accessibility
description: Accessibility patterns for React (web SPA) and React Native. Covers semantic markup, ARIA roles and labels, focus management, keyboard navigation, touch target sizes, dynamic type / OS font scaling, reduced motion, color contrast guidance, and screen reader paths. Use when designing or reviewing any UI feature, when extracting design context from Figma, when shipping interactive components (dialogs, menus, forms, lists), or when a feature claims to be "user-facing".
---

# React Accessibility

Accessibility is not a polish step. Failing a11y means the feature does not work for some users — treat it as a correctness issue, not a nice-to-have.

## Web (React SPA)

### Semantic HTML first
- Use the semantically correct element before reaching for ARIA: `<button>`, `<a href>`, `<nav>`, `<main>`, `<form>`, `<label>`. ARIA is a **patch**, not a default.
- A `<div onClick>` is not a button. It needs `role="button"`, `tabIndex={0}`, keyboard handlers, focus styling, and a label. By the time you've added all that, you should have just used `<button>`.

### ARIA — minimum required
- **Labels**: every interactive element has an accessible name (`aria-label`, `aria-labelledby`, or visible text).
- **Roles**: don't override semantic roles unless you know why (`role="button"` on a `<button>` is redundant and a smell).
- **State**: `aria-expanded`, `aria-selected`, `aria-checked`, `aria-pressed`, `aria-disabled` reflect the real state.
- **Live regions**: `aria-live="polite"` for non-urgent updates (toasts, results count); `assertive` only for urgent errors.

### Focus management
- **Visible focus ring** on all focusable elements. Never `outline: none` without a replacement.
- **Modal/dialog**: trap focus inside; restore focus to the trigger on close; ESC closes.
- **Route change**: move focus to the page heading or main content (screen readers don't auto-announce SPA navigations).
- **Keyboard order**: matches visual order. Don't rely on `tabindex` >0; use document order.

### Forms
- Every input has a `<label htmlFor>`; placeholders are not labels.
- Errors associated via `aria-describedby` and announced via `aria-live`.
- Submit produces feedback (success message, error focus) that screen readers can hear.

### Anti-patterns
- Click handlers on non-interactive elements without keyboard equivalents.
- Custom dropdowns that don't manage focus or arrow-key navigation.
- "Skip to content" link missing on pages with heavy navigation.
- Color-only signaling (red text without an icon or message).

## React Native

### Required props
- **`accessible`**: groups child elements into one accessibility node when needed.
- **`accessibilityRole`**: `'button' | 'link' | 'header' | 'image' | 'switch' | ...`.
- **`accessibilityLabel`**: human-readable name (override the visible text only when needed).
- **`accessibilityState`**: `{ disabled, selected, checked, expanded, busy }`.
- **`accessibilityHint`**: explains the result of activating, when not obvious.

### Touch targets
- Minimum **44 × 44 pt** on iOS, **48 × 48 dp** on Android. If the visual is smaller, expand the hit area with `hitSlop`.

### Dynamic type / font scaling
- Use the project's typography tokens that already respect OS font scale.
- Don't disable scaling globally (`allowFontScaling={false}`) — only locally for layout-critical labels (e.g. tab bar) and even then, prefer a clamp.

### Reduced motion
- `useReducedMotion` from `react-native-reanimated` (or `AccessibilityInfo.isReduceMotionEnabled()`).
- Disable non-essential transitions / parallax / autoplay when enabled.

### Screen reader paths
- Test with **VoiceOver** (iOS) and **TalkBack** (Android) for any new flow.
- Order matters: VoiceOver reads left-to-right, top-to-bottom. If your design relies on absolute positioning, the reading order may need explicit ordering via `accessibilityElementsHidden` / `importantForAccessibility`.

### Anti-patterns
- Pressables under 44pt without `hitSlop`.
- Decorative images without `accessibilityElementsHidden` (screen reader announces filenames).
- Icon-only buttons without `accessibilityLabel`.
- Disabling font scaling app-wide.

## Cross-platform: design-driven a11y

When extracting from Figma or specs, capture (do not fix here):
- Are touch targets large enough?
- Are interactive states (focus, hover on web; pressed on RN) drawn?
- Is information color-only or does it have an icon/label backup?
- Does contrast appear sufficient (call out, the architect/designer decides)?
- Are focus order and tab order obvious from the visual hierarchy?

## Quick checklist (all platforms)

- [ ] Every interactive element has an accessible name.
- [ ] Every interactive element is reachable by keyboard (web) or screen reader (RN).
- [ ] Focus is visible; never `outline: none` without replacement.
- [ ] Modals trap focus; ESC closes (web); back button closes (RN).
- [ ] Route/screen change moves focus appropriately.
- [ ] Touch targets ≥44×44.
- [ ] No color-only signaling.
- [ ] Forms have associated labels and announceable error states.
- [ ] Reduced-motion preference respected.
- [ ] Decorative images hidden from assistive tech; informative images labeled.
