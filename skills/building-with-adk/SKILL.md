---
name: building-with-adk
description: Use when creating a new ADK agent, adding tools to an existing agent, or deploying ADK agents to production
---

<skill>

  <purpose>
    Workflow for building with Google ADK: creating agents, implementing tools, testing locally, and deploying.
  </purpose>

  <triggers>
    <rule>Use when creating a new ADK agent project.</rule>
    <rule>Use when adding tools or sub-agents to an existing ADK agent.</rule>
    <rule>Use when deploying an ADK agent to Vertex AI or Cloud Run.</rule>
  </triggers>

  <gate name="check-adk-version">
    Before starting: verify ADK version with `pip show google-adk`. ADK evolves rapidly — patterns differ between versions. Check the installed version matches the docs you're referencing.
  </gate>

  <process>
    <step>**Project structure** — Create: `agent.py` (agent definition), `tools.py` (tool implementations), `__init__.py` (exports agent), `.env` (API keys for local dev). ADK CLI expects an `agent` module with an exported `root_agent`.</step>
    <step>**Define agent** — Set model, instruction, tools. Keep instructions focused — one agent, one job. If scope creeps, split into sub-agents.</step>
    <step>**Implement tools** — Python functions with type hints and docstrings. Use `ToolContext` for session state access. Test tools as plain functions first.</step>
    <step>**Test locally** — `adk web` for interactive UI, `adk run` for CLI. Verify: tools invoke correctly, session state persists, responses are appropriate.</step>
    <step>**Deploy** — Choose target: `adk deploy cloud_run` for containerized, or Vertex AI Agent Engine for managed. Configure auth, secrets, and service account.</step>
  </process>

  ## Project structure

  ```
  my-agent/
    __init__.py          # from .agent import root_agent
    agent.py             # Agent definition
    tools.py             # Tool implementations
    sub_agents/          # Optional: sub-agent modules
      researcher.py
      writer.py
    .env                 # GOOGLE_API_KEY for local dev
    requirements.txt     # google-adk, dependencies
  ```

  ## Tool implementation pattern

  ```python
  from google.adk.tools import tool, ToolContext

  @tool
  def search_database(query: str, limit: int = 10, ctx: ToolContext = None) -> dict:
      """Search the product database.

      Args:
          query: Search query string.
          limit: Maximum results to return.
      """
      # Access session state if needed
      user_prefs = ctx.session.state.get("preferences", {})

      results = db.search(query, limit=limit, **user_prefs)
      return {"results": results, "count": len(results)}
  ```

  ## Multi-agent setup

  ```python
  researcher = Agent(
      name="researcher",
      model="gemini-2.0-flash",
      instruction="Research topics using available tools. Return structured findings.",
      tools=[web_search, document_search],
  )

  root_agent = Agent(
      name="coordinator",
      model="gemini-2.5-pro",
      instruction="Coordinate research and writing. Delegate research to specialist.",
      sub_agents=[researcher],
      tools=[write_output],
  )
  ```

  <rules>
    <rule>Export `root_agent` from `__init__.py` — ADK CLI expects this.</rule>
    <rule>Keep tool docstrings clear and concise — the LLM uses them to decide when to call the tool.</rule>
    <rule>Test tools as standalone functions before wiring to agent — isolate logic from agent loop.</rule>
    <rule>Use `InMemorySessionService` for local dev, switch to persistent service for deployment.</rule>
    <rule>Set `GOOGLE_API_KEY` in `.env` for local dev. In production, use ADC (Application Default Credentials).</rule>
  </rules>

  <antipattern>
    Putting all logic in tool functions. Keep tools thin — call into your application layer. Tools are the interface between the LLM and your code, not the code itself.
  </antipattern>

  <antipattern>
    One mega-agent with 20+ tools. LLMs struggle with large tool sets. Split into sub-agents with focused tool sets (5-8 tools each).
  </antipattern>

</skill>
