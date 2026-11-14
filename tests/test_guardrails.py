import pytest
from pydantic import BaseModel, Field
from agent_guardrails import (
    BudgetExceededError,
    GuardrailSession,
    InfiniteLoopDetected,
)


class SearchArgs(BaseModel):
    query: str = Field(..., min_length=3)
    limit: int = Field(default=5, ge=1, le=20)


def dummy_search(query: str, limit: int = 5) -> str:
    return f"Results for '{query}' (limit={limit})"


def test_successful_tool_execution():
    session = GuardrailSession(max_steps=5)
    res = session.execute_tool("search", dummy_search, {"query": "python"}, schema=SearchArgs)
    assert res["status"] == "success"
    assert "python" in res["output"]
    assert session.current_steps == 1


def test_auto_healing_validation_error():
    session = GuardrailSession(max_steps=5)
    res = session.execute_tool("search", dummy_search, {"query": "hi"}, schema=SearchArgs)
    assert res["status"] == "error"
    assert res["recoverable"] is True
    assert "validation failed" in res["message"].lower()


def test_infinite_loop_detection():
    session = GuardrailSession(max_steps=10, max_duplicate_calls=2)
    session.execute_tool("search", dummy_search, {"query": "stuck"})
    session.execute_tool("search", dummy_search, {"query": "stuck"})

    with pytest.raises(InfiniteLoopDetected):
        session.execute_tool("search", dummy_search, {"query": "stuck"})


def test_step_budget_circuit_breaker():
    session = GuardrailSession(max_steps=2)
    session.execute_tool("search", dummy_search, {"query": "one"})
    session.execute_tool("search", dummy_search, {"query": "two"})

    with pytest.raises(BudgetExceededError):
        session.execute_tool("search", dummy_search, {"query": "three"})


def test_token_budget_circuit_breaker():
    session = GuardrailSession(max_tokens=1000)
    session.record_tokens(600)
    with pytest.raises(BudgetExceededError):
        session.record_tokens(500)
