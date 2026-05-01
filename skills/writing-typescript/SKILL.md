---
name: writing-typescript
description: Use when actively writing or refactoring TypeScript — choosing unknown/any/generics, narrowing types (predicates, satisfies, discriminated unions), Result vs. throw error handling, structuring tsconfig for a new project — hands-on authoring
---

<skill>

  <purpose>
    Workflow for writing TypeScript: project setup, type design decisions, and common operations.
  </purpose>

  <triggers>
    <rule>Use when writing new TypeScript modules or files.</rule>
    <rule>Use when designing types for a new feature or API.</rule>
    <rule>Use when setting up or modifying tsconfig.</rule>
  </triggers>

  <gate name="check-existing-conventions">
    Before writing new TypeScript: check existing code for patterns. Match the project's style for imports, type definitions, error handling, and exports. Don't introduce new conventions without explicit decision.
  </gate>

  <process>
    <step>**Check project conventions** — Scan existing files for: import style (named vs default), type location (co-located vs `/types`), error handling pattern, export style.</step>
    <step>**Design types first** — Define the types/interfaces for the feature before implementation. Types are the API contract.</step>
    <step>**Implement with inference** — Let TypeScript infer where it can. Add explicit types at boundaries: function params, return types of exported functions, public API.</step>
    <step>**Verify** — `tsc --noEmit` for type checking, then run tests.</step>
  </process>

  <rules>
    <rule>**Export types explicitly** — `export type { Foo }` for type-only exports (enables erasure, prevents accidental runtime dependency).</rule>
    <rule>**Co-locate types** — put types in the same file as their implementation unless shared across 3+ modules.</rule>
    <rule>**Return types on exports** — explicit return types on exported functions improve error messages and prevent accidental API changes.</rule>
    <rule>**Narrow early** — validate at boundaries (function entry, API responses), then work with narrowed types downstream.</rule>
    <rule>**Use `const` assertions** — `as const` for literal objects/arrays that shouldn't widen: `const ROUTES = [...] as const`.</rule>
  </rules>

  ## Type design guidelines

  **Start narrow, widen later.** It's easy to make a type accept more; hard to make it accept less without breaking callers.

  **Prefer composition over inheritance:**
  ```typescript
  // Instead of class hierarchy
  type Logger = { log: (msg: string) => void }
  type TimedLogger = Logger & { elapsed: () => number }
  ```

  **Make invalid states unrepresentable:**
  ```typescript
  // Bad: both fields optional, unclear which combos are valid
  type Response = { data?: Data; error?: Error }
  // Good: exactly one state at a time
  type Response = { status: 'ok'; data: Data } | { status: 'error'; error: Error }
  ```

  **Zod for runtime validation:**
  ```typescript
  const UserSchema = z.object({ name: z.string(), age: z.number().min(0) })
  type User = z.infer< typeof UserSchema >  // derive type from schema
  ```

  <antipattern>
    Defining types in a central `types.ts` barrel file. Co-locate types with their implementation — barrel files create circular dependencies and make dead code elimination harder.
  </antipattern>

  <antipattern>
    Using `any` to "fix" type errors quickly. Use `unknown` + type guard, or fix the actual type mismatch. `any` spreads silently through inference.
  </antipattern>

  ## tsconfig essentials

  ```jsonc
  {
    "compilerOptions": {
      "strict": true,
      "noUncheckedIndexedAccess": true,  // arrays/objects may be undefined
      "exactOptionalPropertyTypes": true, // distinguishes missing from undefined
      "moduleResolution": "bundler",      // for Vite/esbuild projects
      "verbatimModuleSyntax": true        // enforces explicit type imports
    }
  }
  ```

</skill>
