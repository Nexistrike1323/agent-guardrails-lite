# agent-guardrails-lite

Lightweight, zero-bloat reliability middleware for LLM agents. Wraps any tool-calling loop (LangGraph, CrewAI, OpenAI, Gemini, or custom Python agents) to prevent runaway costs, infinite loops, and schema crashes.

## Features

- **Infinite Loop Detection:** SHA-256 hashes `(tool_name, arguments)` on every step and halts execution if an agent repeats identical calls beyond `max_duplicate_calls`.
- **Step & Token Circuit Breakers:** Enforces strict hard ceilings (`max_steps`, `max_tokens`) before an agent burns API credits.
- **Auto-Healing Schema Validation:** Validates raw LLM tool arguments against Pydantic models and returns structured error feedback so the agent can self-correct on the next turn.
- **Structured JSON Telemetry:** Records step latency, arguments, status, and output previews for instant debugging.

## Quickstart

```bash
pip install -e .
```

```python
from pydantic import BaseModel
from agent_guardrails import GuardrailSession, InfiniteLoopDetected

class SearchSchema(BaseModel):
    query: str

def web_search(query: str) -> str:
    return f"Top results for {query}"

session = GuardrailSession(max_steps=8, max_tokens=12000, max_duplicate_calls=2)

try:
    result = session.execute_tool("web_search", web_search, {"query": "AI agents"}, schema=SearchSchema)
    print(result)
except InfiniteLoopDetected as e:
    print(f"Loop prevented: {e}")
```

## Running Tests & Demo

```bash
pytest -v
python examples/demo_agent.py
```
