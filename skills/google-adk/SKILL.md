---
name: google-adk
description: Use when building AI agents with Google Agent Development Kit (ADK), configuring agent tools, or designing multi-agent systems with ADK
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
    <rule>**Agent = LLM + tools + instructions** — an `Agent` wraps a model with system instructions and a set of tools it can invoke. The agent loop: receive input → think → call tools → respond.</rule>
    <rule>**Tools are Python functions** — decorated with `@tool` or registered via `FunctionTool`. Docstrings become the tool description the LLM sees. Type hints become parameter schemas.</rule>
    <rule>**Session state** — `ctx.session.state` is a dict persisted across turns within a session. Use for conversation memory, user preferences, accumulated data.</rule>
    <rule>**Multi-agent via delegation** — agents can have `sub_agents`. Parent delegates to child via natural language routing or explicit transfer. Each sub-agent has its own tools and instructions.</rule>
    <rule>**Callbacks for control** — `before_tool_call`, `after_tool_call`, `before_agent_call` callbacks intercept the agent loop for logging, validation, or overriding behavior.</rule>
    <rule>**Model selection** — `model="gemini-2.0-flash"` for fast/cheap, `model="gemini-2.5-pro"` for complex reasoning. Specify in Agent constructor.</rule>
    <rule>**Structured output** — use `output_schema` parameter with a Pydantic model to get typed JSON responses from the agent.</rule>
    <rule>**Grounding** — `google_search` tool for real-time web info. Vertex AI Search for enterprise corpus. RAG via custom retrieval tools.</rule>
  </rules>

  ## Core architecture

  ```
  Agent(
    name="agent-name",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant that...",
    tools=[tool_a, tool_b],
    sub_agents=[specialist_agent],
  )
  ```

  **Runner** executes the agent loop: `Runner(agent=agent, session_service=session_service)`. Call `runner.run(user_id, session_id, message)` to get a streaming or complete response.

  **Session service** — `InMemorySessionService` for dev, `DatabaseSessionService` for persistence, `VertexAiSessionService` for managed deployment.

  ## Tool patterns

  | Pattern | Use case |
  |---|---|
  | `@tool` decorator | Simple stateless function tools |
  | `FunctionTool(fn)` | Programmatic registration |
  | `ToolContext` param | Access session state, auth tokens within tool |
  | `long_running=True` | Async operations that take time |
  | `auth_config` | Tools requiring user OAuth (Google APIs, etc.) |

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
  | Local dev | `adk web` or `adk run` CLI |
  | Vertex AI Agent Engine | `agent_engines.create(agent=agent)` — fully managed |
  | Cloud Run | Containerize with `adk deploy cloud_run` or custom Dockerfile |
  | Custom server | Use `Runner` in FastAPI/Flask, manage sessions yourself |

</skill>
