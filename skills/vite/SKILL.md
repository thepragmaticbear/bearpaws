---
name: vite
description: Use as a reference for Vite mechanics — dev server vs. build pipeline, plugin model and ordering, HMR, import.meta.env conventions, SSR mode. The *how Vite works*. Pair with working-with-vite for hands-on workflow
---

<skill>

  <purpose>
    Reference knowledge for Vite projects: dev server, build pipeline, plugin system, and common configuration patterns.
  </purpose>

  <triggers>
    <rule>Use when a project has vite.config.ts/js or uses Vite as build tool.</rule>
    <rule>Use when debugging Vite dev server, HMR, or build issues.</rule>
    <rule>Use when configuring Vite plugins or optimization settings.</rule>
  </triggers>

  <rules>
    <rule>**Dev server is ESM-native** — Vite serves unbundled ESM in dev. No bundling during development. Pre-bundles deps with esbuild for CJS→ESM conversion.</rule>
    <rule>**Build uses Rollup** — Production builds use Rollup under the hood. Rollup plugin API applies. Output is optimized bundles with tree-shaking.</rule>
    <rule>**Config is typed** — `defineConfig()` provides type safety. Supports conditional config via function form: `export default defineConfig(({ command, mode }) => ({...}))`.</rule>
    <rule>**Environment variables** — Only `VITE_`-prefixed env vars are exposed to client code via `import.meta.env`. Server-only vars stay private.</rule>
    <rule>**HMR boundary** — HMR propagates up the module graph. If a module can't self-accept, the update bubbles to the nearest accepting ancestor. React Fast Refresh handles component HMR automatically.</rule>
    <rule>**Import aliases** — Configure `resolve.alias` in vite config. Must also mirror in tsconfig paths for type resolution.</rule>
    <rule>**Static assets** — Files in `public/` served at root. Imported assets get hashed filenames. Use `?url`, `?raw`, `?worker` suffixes for special handling.</rule>
    <rule>**CSS modules** — `.module.css` files auto-scoped. PostCSS config auto-detected. Tailwind, Sass, Less work with just the preprocessor installed.</rule>
    <rule>**Library mode** — `build.lib` for building libraries. Specify entry, formats (es, cjs, umd), and external deps. Generates type declarations with `vite-plugin-dts`.</rule>
  </rules>

  ## Common configuration patterns

  | Need | Config |
  |---|---|
  | Proxy API calls | `server.proxy: { '/api': 'http://localhost:3000' }` |
  | Custom port | `server.port: 5174` |
  | Base path (subdir deploy) | `base: '/app/'` |
  | Multi-page app | `build.rollupOptions.input: { main: 'index.html', nested: 'nested/index.html' }` |
  | Externalize deps | `build.rollupOptions.external: ['react', 'react-dom']` |
  | Chunk splitting | `build.rollupOptions.output.manualChunks` |
  | SSR | `ssr: { external: [...], noExternal: [...] }` |
  | Worker threads | `import Worker from './worker?worker'` |

  ## Plugin system

  Vite plugins extend both dev and build. Plugin hooks run in order: `config` → `configResolved` → `configureServer` → `transformIndexHtml` → `resolveId` → `load` → `transform`.

  **Common plugins:** `@vitejs/plugin-react` (React Fast Refresh + JSX), `@vitejs/plugin-vue` (SFC support), `vite-plugin-dts` (type declarations), `vite-plugin-pwa` (service workers).

  **Enforce order:** `enforce: 'pre'` runs before core plugins, `enforce: 'post'` runs after.

  ## Debugging

  | Problem | Likely cause |
  |---|---|
  | HMR not updating | Missing `accept` in custom modules; check for full-page reload in console |
  | Slow cold start | Too many deps to pre-bundle; check `optimizeDeps.include` |
  | Build fails, dev works | CJS dep not pre-bundled for build; add to `ssr.noExternal` or `optimizeDeps.include` |
  | Env var undefined | Missing `VITE_` prefix for client code |
  | CORS in dev | Missing proxy config; API on different origin |
  | Types not found | `resolve.alias` not mirrored in `tsconfig.json` paths |

</skill>
