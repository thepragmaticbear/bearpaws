---
name: working-with-vite
description: Use when setting up a new Vite project, adding features to Vite config, or troubleshooting Vite dev/build issues
---

<skill>

  <purpose>
    Workflow for common Vite operations: project setup, adding plugins, configuring builds, and fixing issues.
  </purpose>

  <triggers>
    <rule>Use when creating a new Vite project or adding Vite to an existing project.</rule>
    <rule>Use when adding plugins, configuring builds, or setting up deployment.</rule>
    <rule>Use when troubleshooting dev server, HMR, or production build issues.</rule>
  </triggers>

  <gate name="check-existing-config">
    Before modifying Vite config: read the existing `vite.config.ts` and `package.json` scripts. Understand what's already configured before making changes.
  </gate>

  <process>
    <step>**Verify Vite project** — Check for `vite.config.ts/js`, confirm `vite` in devDependencies, identify framework plugin (React/Vue/Svelte).</step>
    <step>**Understand current config** — Read config file, check for custom plugins, aliases, proxy settings, env mode handling.</step>
    <step>**Make targeted changes** — Modify config for the specific need. Don't restructure working config.</step>
    <step>**Test in dev** — `npm run dev` (or equivalent). Verify: server starts, HMR works, no console errors.</step>
    <step>**Test build** — `npm run build && npm run preview`. Verify: build succeeds, preview renders correctly, assets load.</step>
  </process>

  ## Common workflows

  **Adding a plugin:**
  ```bash
  npm install -D {plugin-name}
  ```
  Then add to `plugins` array in vite.config.ts. Most plugins are just `pluginName()` with no config needed.

  **Setting up path aliases:**
  ```typescript
  // vite.config.ts
  resolve: { alias: { '@': path.resolve(__dirname, './src') } }
  ```
  Mirror in `tsconfig.json`: `"paths": { "@/*": ["./src/*"] }`

  **Proxy for API:**
  ```typescript
  server: { proxy: { '/api': { target: 'http://localhost:3000', changeOrigin: true } } }
  ```

  **Environment-specific config:**
  ```typescript
  export default defineConfig(({ command, mode }) => {
    const env = loadEnv(mode, process.cwd(), '')
    return { /* config using env */ }
  })
  ```

  <rules>
    <rule>Always test both `dev` and `build` after config changes — they use different pipelines.</rule>
    <rule>Keep `optimizeDeps.include` minimal — only add deps that cause issues.</rule>
    <rule>Match `resolve.alias` in both vite config AND tsconfig for type safety.</rule>
    <rule>Use `VITE_` prefix for any env var needed in client code.</rule>
  </rules>

  <antipattern>
    Blindly adding `optimizeDeps.include` for every dependency. Only pre-bundle deps that cause ESM/CJS issues in dev.
  </antipattern>

  <antipattern>
    Configuring proxy in Vite for production. Proxy only works in dev server — production needs actual API routing (nginx, cloud function, etc.).
  </antipattern>

</skill>
