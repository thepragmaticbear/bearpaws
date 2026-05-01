---
name: javascript-typescript
description: Use as a reference for JS/TS language mechanics — ES2022+ idioms, TS 5.x type system, behavior-changing tsconfig flags, ESM/CJS interop, Node vs. browser vs. worker resolution. Pair with writing-typescript for active authoring decisions
---

<skill>

  <purpose>
    Reference knowledge for JavaScript/TypeScript projects: type system, module patterns, runtime behavior, and common gotchas.
  </purpose>

  <triggers>
    <rule>Use when working in a JS/TS codebase and encountering type errors or design decisions.</rule>
    <rule>Use when choosing between patterns (classes vs functions, enums vs unions, etc.).</rule>
    <rule>Use when debugging runtime issues related to JS/TS specifics (async, closures, `this`).</rule>
  </triggers>

  <rules>
    <rule>**Prefer `type` over `interface`** unless you need declaration merging or class implements. Types are more composable (unions, intersections, mapped types).</rule>
    <rule>**Prefer discriminated unions over enums** — `type Status = 'active' | 'inactive'` is exhaustive-check-friendly and doesn't emit runtime code.</rule>
    <rule>**Use `satisfies`** for type-safe object literals that preserve narrow types: `const config = {...} satisfies Config`.</rule>
    <rule>**Avoid `any`** — use `unknown` for truly unknown values, then narrow with type guards. `any` disables all type checking downstream.</rule>
    <rule>**Avoid `as` casts** — they silence the compiler. Prefer type guards, `satisfies`, or restructuring code so inference works.</rule>
    <rule>**Module system** — use ESM (`import`/`export`). CJS (`require`) only for Node.js legacy or config files. Never mix in the same file.</rule>
    <rule>**Strict mode** — always enable `strict: true` in tsconfig. Subset flags (`strictNullChecks`, `noImplicitAny`) are subsumed.</rule>
    <rule>**Avoid `null`** — prefer `undefined` for absent values (matches optional params and destructuring defaults). Use `null` only for explicit "empty" semantics from APIs.</rule>
    <rule>**Async/await over raw promises** — cleaner error handling with try/catch, clearer flow, better stack traces. Only use `.then()` for simple one-liners.</rule>
    <rule>**No floating promises** — every async call must be `await`ed, returned, or explicitly voided with `void promise`. Unhandled rejections crash Node 15+.</rule>
  </rules>

  ## Type patterns

  | Need | Pattern |
  |---|---|
  | Narrow from union | Discriminated union: `type Shape = { kind: 'circle'; r: number } \| { kind: 'rect'; w: number; h: number }` |
  | Safe object access | Optional chaining: `obj?.nested?.value` |
  | Exhaustive switch | `default: const _: never = value` |
  | Partial updates | `Partial` utility type for optional fields |
  | Required subset | `Pick` or `Required` with key union |
  | Exclude fields | `Omit` with key union |
  | Map over keys | `Record` or mapped type `{ [K in keyof T]: ... }` |
  | Infer return type | `ReturnType` utility with typeof |
  | Branded types | `type UserId = string & { __brand: 'UserId' }` |

  ## Common gotchas

  | Issue | Cause | Fix |
  |---|---|---|
  | `Type 'X' is not assignable to 'Y'` | Structural mismatch | Check exact property differences; often a missing optional field |
  | `Object is possibly undefined` | Nullable access without narrowing | Add null check, optional chaining, or non-null assertion (last resort) |
  | `this` is undefined | Arrow vs function context | Use arrow functions in callbacks; class methods need binding or arrows |
  | `Cannot find module` | Path/extension mismatch | Check tsconfig paths, file extensions, `moduleResolution` setting |
  | Implicit any on callback params | Generic inference failure | Add explicit type annotation to the parameter |
  | `readonly` not enforced at runtime | TS types are compile-time only | Use `Object.freeze()` if runtime immutability needed |

  ## Performance-aware patterns

  - **Avoid creating objects in render paths** — memoize with `useMemo`/`useCallback` in React, or hoist constants.
  - **Use `Map`/`Set`** for frequent lookup/membership — O(1) vs array O(n).
  - **Prefer `for...of`** over `.forEach()` for early exit with `break`/`return`.
  - **Structure sharing** — spread creates shallow copies. For deep updates, use immer or structured-clone only when needed.

</skill>
