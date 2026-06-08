---
name: react-native-architecture
description: Patterns and pitfalls for React Native development. Covers list virtualization (FlatList, SectionList), Reanimated/worklets, platform-specific files, navigation lifecycle (React Navigation), image performance, deep linking, Hermes/JSI, AppState, and memory/cleanup. Use when designing or reviewing in a React Native codebase, or when stack detection identifies `ios/`/`android/` folders, `react-native` in `package.json`, or React Navigation usage.
---

# React Native Architecture

Mobile-first patterns. Every decision must consider iOS, Android, and low-end devices. If the project is web-only React, this skill does not apply.

## Lists & virtualization

### Defaults
- **`FlatList`** for any homogeneous list >20 items. **`SectionList`** for grouped data.
- **Never** use `<ScrollView>{items.map(...)}</ScrollView>` for >20 items. It mounts every row at once.
- **`keyExtractor`** is required; never rely on default `index` extraction (breaks reorder/animation).

### Tuning
- **`getItemLayout`** when row height is fixed → enables instant scroll-to-index and skips measurement.
- **`removeClippedSubviews`** on heavy lists (Android benefits more than iOS).
- **`initialNumToRender`** ≈ what fits on screen; **`maxToRenderPerBatch`** small (e.g. 5–10); **`windowSize`** (default 21) tune down to reduce memory.
- Memoize `renderItem` — passing an inline arrow re-renders all rows on every parent render.

### Anti-patterns
- Nested `<FlatList>` inside `<ScrollView>` without `nestedScrollEnabled` (Android) and proper handling.
- `key={index}` in lists that can reorder.
- Heavy work in `renderItem` (deep object spreads, date parsing) — push it into the data layer.

## Animations & gestures

### Reanimated
- Worklets run on the **UI thread**. Do not access JS state, refs, or non-shared values inside a worklet without `runOnJS`.
- `useAnimatedStyle` deps must include every shared value it reads.
- Cancel animations on unmount (`cancelAnimation(sharedValue)`) for pages that mount/unmount frequently.
- Prefer Reanimated 3 APIs (`useSharedValue`, `useAnimatedStyle`, `withTiming`); `Animated` (legacy) only for tiny one-offs.

### Gesture Handler
- All gesture handlers must be the latest `react-native-gesture-handler` API.
- Wrap the app in `GestureHandlerRootView`; on Android this is mandatory or gestures silently fail.

### Anti-patterns
- Driving animations from `useState` + `setInterval` instead of Reanimated.
- Reading `sharedValue.value` inside `render` (only valid in worklets / `useAnimatedStyle`).

## Navigation (React Navigation)

### Defaults
- **Stack** for hierarchical flows; **Bottom Tab** for top-level destinations; **Native Stack** when you want native transitions and don't need deep customization.
- **`useFocusEffect`** instead of `useEffect` when behavior should pause when the screen is not focused (e.g. polling, listeners).
- **Cleanup** every focus listener, subscription, animation, timer in the return of `useFocusEffect` / `useEffect`.

### Deep linking
- Centralize the linking config; type the param shape.
- Validate parsed deep link params before navigating — never pass untrusted values straight to `navigate()`.
- State restoration: opt in (`getInitialState`) only with a TTL; stale state is a UX trap.

### Anti-patterns
- Mutating navigation state via global store instead of using the navigation API.
- `navigation.navigate('Foo', { ...heavyObject })` — only pass IDs, fetch on the destination screen.
- Listeners registered in `useEffect` with `[]` deps that read stale closures.

## Platform-specific code

- Prefer file-extension splits (`Foo.ios.tsx`, `Foo.android.tsx`) for components that diverge structurally.
- Use `Platform.select({ ios: ..., android: ... })` for one-line value differences.
- Avoid deep `if (Platform.OS === 'ios')` ladders inside one component — extract into `*.ios.tsx`/`*.android.tsx`.
- For web-only RN (RNW), use `*.web.tsx`; do not commingle DOM-only code in shared files.

## Images

- **Always** specify `width`/`height` (or aspect ratio) for remote images; layout shifts on slow networks otherwise.
- **`resizeMode`** explicit (`cover`/`contain`); the default differs by component.
- For long lists with remote images, consider **`react-native-fast-image`** (Android caching) or `expo-image`.
- Lazy-load below-the-fold images; consider thumbnail → full swap.

## Memory & lifecycle

- Clean up: timers (`clearTimeout`), intervals, event listeners (`Linking`, `AppState`, `Keyboard`), subscriptions (sockets), animations, gesture handlers.
- `AppState` for foreground/background transitions: refresh data on `'active'`, pause sensitive work on `'background'`.
- WebView: lock `originWhitelist`; never enable `javaScriptEnabled` for untrusted URLs.

## Hermes & New Architecture

- **Hermes**: default for both platforms now. Watch for unsupported `Intl` APIs on older versions; provide polyfills if needed.
- **New Architecture (Fabric/TurboModules)**: when migrating, audit:
  - Native modules that use the old bridge.
  - Synchronous bridge calls that don't survive TurboModule semantics.
  - Old `findNodeHandle` usage.

## Permissions & native modules

- Request permissions with a clear pre-prompt rationale; never call permission APIs on app launch without context.
- Wrap native modules in a typed JS facade; never call them directly from screens.

## Quick checklist

- [ ] Lists use `FlatList`/`SectionList` with `keyExtractor`; no `ScrollView` over `.map` for non-trivial counts.
- [ ] `renderItem` is memoized; row component is `React.memo`.
- [ ] Animations on UI thread (Reanimated worklets); no `setInterval`-driven UI.
- [ ] All listeners/timers cleaned up on unmount or focus loss.
- [ ] Platform-divergent components use `*.ios.tsx`/`*.android.tsx`, not nested `Platform.OS` ladders.
- [ ] Remote images have dimensions and explicit `resizeMode`.
- [ ] Deep link params validated before navigation.
- [ ] WebViews lock `originWhitelist` and disable JS for untrusted URLs.
- [ ] `GestureHandlerRootView` wraps the app on Android.
- [ ] Sensitive UI handles `AppState` background transitions.
