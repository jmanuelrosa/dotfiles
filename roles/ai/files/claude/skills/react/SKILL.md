---
name: developing-react
description: >
  React, Next.js, and component architecture guidelines. Use when writing,
  reviewing, or refactoring React/Next.js code. Triggers on: component design,
  data fetching, bundle optimization, re-render issues, composition patterns,
  compound components, server components, or performance work.
license: MIT
metadata:
  date: 08-March-2026
  version: "1.0.0"
  sources:
    - https://github.com/vercel-labs/agent-skills/tree/main/skills/react-best-practices
    - https://github.com/vercel-labs/agent-skills/tree/main/skills/composition-patterns
    - https://github.com/millionco/react-doctor/blob/main/skills/react-doctor/SKILL.md
---

# React Development Guide

Consolidated rules for React/Next.js: component architecture, performance optimization, and composition patterns.

## Quick Health Check

After making React changes, run:

```bash
npx -y react-doctor@latest . --verbose --diff
```

Fix errors first, re-run to verify score improved.

## 1. Component Architecture (HIGH)

<!-- via: composition-patterns -->

### Avoid Boolean Prop Proliferation

Each boolean doubles possible states. Use composition instead.

```tsx
// BAD: exponential complexity
<Composer isThread isEditing={false} channelId="abc" showAttachments />

// GOOD: explicit variants
<ThreadComposer channelId="abc" />
<EditMessageComposer messageId="xyz" />
```

Each variant composes shared parts explicitly. No hidden conditionals.

### Compound Components with Shared Context

Structure complex components as compound components. Subcomponents access shared state via context, not props.

```tsx
const ComposerContext = createContext<ComposerContextValue | null>(null)

function ComposerProvider({ children, state, actions, meta }: ProviderProps) {
  return (
    <ComposerContext value={{ state, actions, meta }}>
      {children}
    </ComposerContext>
  )
}

// Subcomponents use context
function ComposerInput() {
  const { state, actions: { update }, meta: { inputRef } } = use(ComposerContext)
  return <TextInput ref={inputRef} value={state.input} onChangeText={(t) => update((s) => ({ ...s, input: t }))} />
}

// Export as compound component
const Composer = { Provider: ComposerProvider, Frame: ComposerFrame, Input: ComposerInput, Submit: ComposerSubmit }
```

### Generic Context Interface

Define `{ state, actions, meta }` interface. Any provider can implement it - same UI works with different state backends.

```tsx
interface ComposerContextValue {
  state: ComposerState
  actions: { update: (updater: (s: ComposerState) => ComposerState) => void; submit: () => void }
  meta: { inputRef: React.RefObject<TextInput> }
}

// Provider A: local state for ephemeral forms
function ForwardMessageProvider({ children }) { /* useState + Composer.Provider */ }
// Provider B: global synced state for channels
function ChannelProvider({ channelId, children }) { /* useGlobalChannel + Composer.Provider */ }
// Same Composer.Input works with both
```

### Lift State into Providers

Move state to provider components so siblings outside the main UI can access it.

```tsx
// ForwardButton lives OUTSIDE Composer.Frame but can still submit
function ForwardButton() {
  const { actions: { submit } } = use(ComposerContext)
  return <Button onPress={submit}>Forward</Button>
}
```

Provider boundary is what matters - not visual nesting.

### Children Over Render Props

Use `children` for composition. Use render props only when parent needs to pass data back (e.g., `renderItem`).

### React 19 API Changes

> React 19+ only. Skip on React 18.

- `ref` is a regular prop - drop `forwardRef`
- `use(Context)` replaces `useContext(Context)` - can be called conditionally

## 2. Eliminating Waterfalls (CRITICAL)

<!-- via: react-best-practices -->

See `references/performance.md` for detailed patterns.

- **Defer await** - move `await` into branches where actually used
- **Promise.all()** - parallelize independent operations
- **Dependency-based parallelization** - use `better-all` or promise chaining for partial deps
- **Start promises early** - in API routes, start independent fetches immediately, await late
- **Suspense boundaries** - wrap async components to stream content; layout renders instantly

```tsx
// BAD: sequential
const user = await fetchUser()
const posts = await fetchPosts()

// GOOD: parallel
const [user, posts] = await Promise.all([fetchUser(), fetchPosts()])
```

## 3. Bundle Size (CRITICAL)

<!-- via: react-best-practices -->

See `references/performance.md` for detailed patterns.

- **Avoid barrel imports** - import directly: `import Check from 'lucide-react/dist/esm/icons/check'`
  - Or use `optimizePackageImports` in next.config.js
- **Dynamic imports** - `next/dynamic` for heavy components (Monaco, charts, maps)
- **Defer third-party** - load analytics/logging after hydration with `{ ssr: false }`
- **Conditional loading** - `import()` only when feature is activated
- **Preload on intent** - `onMouseEnter`/`onFocus` to preload heavy bundles

## 4. Server-Side Performance (HIGH)

<!-- via: react-best-practices -->

See `references/performance.md` for detailed patterns.

- **Auth server actions** - always verify auth inside `"use server"` functions; they're public endpoints
- **React.cache()** - per-request deduplication (auth, DB queries). Use primitive args (not inline objects)
- **LRU cache** - cross-request caching with `lru-cache` for sequential user actions
- **Minimize RSC serialization** - only pass fields client actually uses
- **Avoid duplicate serialization** - don't transform arrays in RSC; do `.filter()`/`.toSorted()` in client
- **Parallel RSC fetching** - restructure component tree so async components are siblings, not nested
- **Hoist static I/O** - fonts, logos, config at module level (runs once, not per request)
- **after()** - schedule logging/analytics after response is sent

## 5. Client-Side Patterns (MEDIUM-HIGH)

<!-- via: react-best-practices -->

- **SWR** - automatic request dedup, caching, revalidation across component instances
- **Deduplicate event listeners** - `useSWRSubscription` to share global listeners
- **Passive listeners** - `{ passive: true }` for touch/wheel (unless you need `preventDefault`)
- **localStorage versioning** - version prefix on keys, store minimal fields, wrap in try-catch

## 6. Re-render Optimization (MEDIUM)

<!-- via: react-best-practices -->

See `references/rendering.md` for detailed patterns.

- **Derive state during render** - don't store computed values in state or sync via effects
- **Defer state reads** - read `searchParams`/localStorage in callbacks, not at render time
- **Extract to memo components** - isolate expensive work behind `memo()` for early returns
- **Hoist default props** - extract non-primitive defaults to constants (`const NOOP = () => {}`)
- **Don't memo simple primitives** - `useMemo` for `a || b` wastes more than it saves
- **Narrow effect deps** - use `user.id` not `user`; derive `isMobile` boolean from `width`
- **Event handlers for side effects** - don't model user actions as state + effect
- **Subscribe to derived state** - `useMediaQuery('(max-width: 767px)')` not `useWindowWidth()`
- **Functional setState** - `setItems(curr => [...curr, item])` prevents stale closures
- **Lazy state init** - `useState(() => expensiveComputation())` runs only once
- **Transitions** - `startTransition` for non-urgent updates (scroll tracking, search)
- **useRef for transient values** - mouse position, intervals, flags that don't need re-render

## 7. Rendering Performance (MEDIUM)

<!-- via: react-best-practices -->

See `references/rendering.md` for detailed patterns.

- **Animate SVG wrapper** - wrap SVG in `<div>`, animate the div (GPU acceleration)
- **content-visibility: auto** - skip layout/paint for off-screen list items
- **Hoist static JSX** - extract constant JSX outside components
- **SVG precision** - reduce to 1 decimal: `npx svgo --precision=1`
- **Hydration no-flicker** - inline `<script>` to set theme/prefs before React hydrates
- **suppressHydrationWarning** - for expected mismatches (dates, random IDs)
- **Activity component** - `<Activity mode="hidden">` preserves state/DOM
- **Ternary over &&** - `count > 0 ? <Badge /> : null` avoids rendering `0`
- **useTransition** - replace manual `isLoading` state with `isPending` from `useTransition`

## 8. JavaScript Performance (LOW-MEDIUM)

<!-- via: react-best-practices -->

- **Avoid layout thrashing** - batch writes then read, or use CSS classes
- **Map for lookups** - `new Map(users.map(u => [u.id, u]))` for repeated `.find()`
- **Cache in loops** - hoist `obj.config.settings.value` outside loop
- **Cache function results** - module-level Map for repeated calls (slugify, etc.)
- **Cache storage reads** - Map wrapper for localStorage/sessionStorage/cookie
- **Combine iterations** - single `for` loop instead of multiple `.filter()` chains
- **Length check first** - before expensive array comparisons
- **Early return** - exit functions as soon as result is determined
- **Hoist RegExp** - to module scope; memoize dynamic patterns with `useMemo`
- **Loop for min/max** - O(n) loop, not O(n log n) sort
- **Set/Map for lookups** - `Set.has()` over `Array.includes()` for repeated checks
- **toSorted()** - immutable sort; never `.sort()` on props/state

## 9. Advanced Patterns (LOW)

<!-- via: react-best-practices -->

- **Init once** - module-level guard (`let didInit = false`) instead of `useEffect([], ...)`
- **Event handler refs** - store callbacks in refs for stable effect subscriptions
- **useEffectEvent** - stable callback that always calls latest handler version
