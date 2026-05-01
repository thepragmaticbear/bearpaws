---
name: onboarding-to-a-project
description: Use FIRST whenever there's an existing project context — before brainstorming, before any domain skill. Identifies key files, stack, and conventions from manifests, README, CLAUDE.md, and similar files. The standard flow is onboarding → brainstorming → implementation. Skip only for purely abstract design discussion with no project to onboard to, or if already onboarded this project earlier in the session
---

<skill>

  <purpose>
    Stack-agnostic onboarding that runs **before** any framework-specific skill. Detect what's actually there, read the team's conventions, sample similar files. Only after that — if a domain skill applies (cloud-run, vite, google-adk, etc.) — layer it on. The order matters: if you reach for `cloud-run` first and impose Cloud Run defaults without first reading the project's existing deploy scripts, secret management, or service-account conventions, your "best practice" suggestion can clash with the team's actual setup.
  </purpose>

  <triggers>
    <rule>Use FIRST whenever there's an existing project context — including before brainstorming a feature for that project. Onboarding identifies what's there; brainstorming designs against it.</rule>
    <rule>Use even when a domain skill clearly applies (e.g. you see a `Dockerfile` and `gcloud run deploy` — still onboard first, then invoke `cloud-run`).</rule>
    <rule>SKIP only for purely abstract design questions with no specific project ("how would I architect a system that does X?" with no project named). When the user references "my app", "this codebase", a directory, or any specific project — onboard.</rule>
    <rule>SKIP if you've already onboarded this project earlier in the session — the conventions you discovered then still apply.</rule>
  </triggers>

  <warning level="hard">
    Don't impose conventions from your training data. Read what's already there first. A pattern used in three places is the convention — even if you'd write it differently from scratch. Domain skills (cloud-run, vite, google-adk, etc.) describe the *general* mechanics of a tool; this project's *specific* conventions override the general guidance every time.
  </warning>

  <rules>
    <rule>**Onboarding before domain skill.** When the project clearly involves Cloud Run / ADK / Vite / TypeScript, complete the onboarding steps below first, *then* invoke the relevant domain skill. The domain skill operates on the conventions you discovered here, not on a blank slate.</rule>
    <rule>**Manifest first.** Read the project's dependency/build manifest before writing any code. It tells you the stack, the build system, the test runner, and (often) the coding conventions.</rule>
    <rule>**README and CLAUDE.md/AGENTS.md** are higher-priority than your priors. If they say "we use X for Y," use X for Y, even if Z is more popular.</rule>
    <rule>**Sample existing files** — find 2-3 files similar to what you're about to write. Match their imports, naming, error handling, test style.</rule>
    <rule>**Run the test command before writing tests.** If you don't know it works, you don't know what RED looks like.</rule>
    <rule>**Ask when ambiguous.** "I see two patterns for X — should I follow A or B?" beats picking one and being wrong.</rule>
  </rules>

  <process>
    <step>**Detect the stack.** Look for manifests in priority order:
      - JS/TS: `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `bun.lockb`
      - Python: `pyproject.toml`, `setup.py`, `requirements.txt`, `Pipfile`, `poetry.lock`, `uv.lock`
      - Go: `go.mod`, `go.sum`
      - Rust: `Cargo.toml`, `Cargo.lock`
      - Ruby: `Gemfile`, `Gemfile.lock`
      - Java/Kotlin: `pom.xml`, `build.gradle`, `build.gradle.kts`, `settings.gradle`
      - .NET: `*.csproj`, `*.fsproj`, `*.sln`, `global.json`
      - Elixir: `mix.exs`, `mix.lock`
      - Swift: `Package.swift`, `*.xcodeproj`
      - Container: `Dockerfile`, `docker-compose.yml`, `compose.yaml`
      - Infrastructure: `terraform`, `*.tf`, `pulumi.yaml`, `Chart.yaml` (Helm)
    </step>
    <step>**Read project guidance.** `README.md`, `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursor/rules/*`, `CONTRIBUTING.md`, `.editorconfig`. These encode team conventions the manifest can't.</step>
    <step>**Find the test command.** From the manifest's `scripts`/`test`/`tasks` block, or `Makefile`, or CI config (`.github/workflows/*`, `.gitlab-ci.yml`, `.circleci/config.yml`). Run it cold once to verify the baseline before changing anything.</step>
    <step>**Find similar files.** For "I'm about to write a service/handler/component/migration", grep for 2-3 existing examples of the same shape. Match their structure.</step>
    <step>**Now layer on domain skills.** If the project uses Cloud Run, invoke `bp:cloud-run` (and `bp:deploying-to-cloud-run` when about to deploy). If Vite, `bp:vite` / `bp:working-with-vite`. If ADK, `bp:google-adk` / `bp:building-with-adk`. The domain skill brings the general mechanics; the conventions you discovered above tell you which mechanics to apply *here*.</step>
    <step>**If no domain skill matches**, that's fine — the discovered conventions plus stack-agnostic process skills (`bp:test-driven-development`, `bp:systematic-debugging`, `bp:writing-plans`, `bp:requesting-code-review`) are sufficient. The stack only changes the *commands you run*, not the *discipline*.</step>
  </process>

  <example type="good">
    User: "Help me add a new endpoint to my service."

    1. Manifest scan: `pyproject.toml` shows FastAPI + SQLAlchemy + pytest. Pinned Python 3.12.
    2. `README.md` mentions the service deploys to Cloud Run via GitHub Actions.
    3. `CLAUDE.md` says the team uses async SQLAlchemy and structured `structlog` for logging.
    4. Test command: `pytest tests/` — runs cold, all green (baseline confirmed).
    5. Sampled `app/routers/user.py` — sees the existing endpoint shape: async function, `Depends()` for DB session, `structlog` for logs, custom `APIError` for failures.
    6. *Now* layer on domain skills: `bp:cloud-run` for deploy semantics, but only when about to ship. The endpoint code follows the project's FastAPI/structlog/async patterns — not generic Flask or print-logging.
    7. Apply `bp:test-driven-development` — write a failing pytest first, in the existing test file's style.
  </example>

  <example type="bad">
    User: "Help me add a new endpoint to my service."

    Bad: jump straight to `bp:cloud-run` because you noticed a Dockerfile, then write an endpoint with generic `print()` logging and a synchronous DB call. The project uses async/structlog and Cloud Run is irrelevant to the *endpoint code*. You imposed framework defaults from training-data priors instead of the project's actual patterns.
  </example>

  <antipattern>
    **Skipping onboarding because "the domain skill obviously applies."** A clear Cloud Run signal doesn't replace reading the project's existing deploy script, secret bindings, IAM bindings, and service-account convention. Domain skill = general mechanics. Onboarding = this project's specifics. Both, in that order.
  </antipattern>

  <antipattern>
    **Imposing your training-data prior.** "Most Python projects use Black/Ruff/uv" is a statement about the population, not this project. Read the project's lint config (`.ruff.toml`, `pyproject.toml [tool.ruff]`, `setup.cfg`, `.flake8`) and match it. If there's none, ask before introducing one.
  </antipattern>

  <antipattern>
    **Defaulting to the most-popular framework option.** Many Vue projects use Pinia, but this one might use Vuex. Many Python projects use pytest, but this one might use unittest. Detect, don't assume.
  </antipattern>

</skill>
