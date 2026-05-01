---
name: google-adk
description: Use as a reference for Google ADK architecture — LlmAgent shapes, Tool/FunctionTool/built-ins, sessions/state/memory, callbacks, runners, Vertex AI Agent Engine vs. Cloud Run targets. Pair with building-with-adk for active scaffolding
---

<skill>

  <purpose>
    Reference knowledge for Google Agent Development Kit (ADK): agent architecture, tool system, multi-agent orchestration, and deployment patterns.
  </purpose>

  <triggers>
    <rule>Use when building agents with Google ADK (Python `google-adk` package).</rule>
    <rule>Use when defining tools, configuring agent behavior, or orchestrating multi-agent systems.</rule>
    <rule>Use when deploying ADK agents to Vertex AI Agent Engine or Cloud Run.</rule>
  </triggers>

  <rules>
    <rule>**Agent = LLM + tools + instructions** — `LlmAgent` (alias `Agent`) wraps a model with system instructions and a set of tools. Loop: receive input → think → call tools → respond.</rule>
    <rule>**Tools are plain Python functions** — pass them directly in `tools=[fn]` and ADK auto-wraps them. Use `FunctionTool(fn)` for explicit registration; `LongRunningFunctionTool(fn)` for async/long-running. Docstrings become the tool description the LLM sees; type hints become parameter schemas. There is no `@tool` decorator.</rule>
    <rule>**Session state** — `tool_context.state` (or `callback_context.state`) is a dict persisted across turns within a session. Use for conversation memory, user preferences, accumulated data.</rule>
    <rule>**Multi-agent via delegation** — agents can have `sub_agents`. Parent delegates via LLM-driven routing or `transfer_to_agent`. Each sub-agent has its own tools and instructions.</rule>
    <rule>**Callbacks for control** — `before_tool_callback`, `after_tool_callback`, `before_agent_callback`, `after_agent_callback`, `before_model_callback`, `after_model_callback` intercept the loop for logging, validation, or overriding.</rule>
    <rule>**Model selection** — `model="gemini-flash-latest"` for fast/cheap (alias; can shift between stable and preview revisions, pin a dated ID for production reproducibility); `model="gemini-2.5-pro"` for complex reasoning. Verify the current SOTA Pro model in Google's model catalog before pinning.</rule>
    <rule>**Structured output** — use `output_schema` with a Pydantic model to get typed JSON responses from the agent.</rule>
    <rule>**Grounding** — `google_search` built-in tool for real-time web info. Vertex AI Search for enterprise corpus. RAG via custom retrieval tools.</rule>
  </rules>

  ## Core architecture

  ```python
  from google.adk.agents import LlmAgent

  root_agent = LlmAgent(
      name="agent-name",
      model="gemini-flash-latest",
      instruction="You are a helpful assistant that...",
      tools=[tool_a, tool_b],
      sub_agents=[specialist_agent],
  )
  ```

  **Runner** executes the agent loop: `Runner(agent=root_agent, session_service=session_service)`. Call `runner.run_async(user_id, session_id, new_message)` to stream events.

  **Session service** — `InMemorySessionService` for dev, `DatabaseSessionService` for persistence, `VertexAiSessionService` for managed deployment.

  ## Tool patterns

  | Pattern | Use case |
  |---|---|
  | Plain function in `tools=[fn]` | Auto-wrapped — the default path for most tools |
  | `FunctionTool(fn)` | Explicit registration when you need a handle |
  | `LongRunningFunctionTool(fn)` | Async / long-running operations |
  | `ToolContext` param | Access `state`, auth tokens, artifacts within a tool |
  | `auth_config=` on a tool | Tools requiring user OAuth (Google APIs, etc.) |

  ## Multi-agent patterns

  | Pattern | Implementation |
  |---|---|
  | Router agent | Parent with `sub_agents`, LLM decides delegation |
  | Pipeline | Agent A output feeds Agent B via `transfer_to_agent` |
  | Specialist pool | Parent delegates domain questions to specialized sub-agents |
  | Critic/reviewer | Output agent + review agent that validates before responding |

  ## Deployment

  | Target | Method |
  |---|---|
  | Local dev | `adk web` (browser UI) or `adk run` (CLI) |
  | Vertex AI Agent Engine | Wrap with `app = reasoning_engines.AdkApp(agent=root_agent, ...)`, then `vertexai.agent_engines.create(agent_engine=app, requirements=[...])` — fully managed |
  | Cloud Run | `adk deploy cloud_run --project=PROJECT_ID --region=REGION` or a custom Dockerfile |
  | Custom server | Wrap `Runner` in FastAPI/Flask, manage sessions yourself |

</skill>
