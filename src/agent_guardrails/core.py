import hashlib
import json
import time
from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel, ValidationError
from .exceptions import BudgetExceededError, InfiniteLoopDetected


class GuardrailSession:
    """Tracks state, tool call hashes, step counts, and telemetry for a single agent run."""

    def __init__(
        self,
        max_steps: int = 10,
        max_tokens: int = 16000,
        max_duplicate_calls: int = 2,
    ):
        self.max_steps = max_steps
        self.max_tokens = max_tokens
        self.max_duplicate_calls = max_duplicate_calls

        self.current_steps = 0
        self.total_tokens = 0
        self._call_counts: Dict[str, int] = {}
        self.trace_logs: List[Dict[str, Any]] = []

    def _hash_call(self, tool_name: str, args: Dict[str, Any]) -> str:
        payload = json.dumps({"tool": tool_name, "args": args}, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def record_tokens(self, tokens_used: int) -> None:
        self.total_tokens += tokens_used
        if self.total_tokens > self.max_tokens:
            raise BudgetExceededError(
                f"Token budget exceeded: {self.total_tokens}/{self.max_tokens} tokens used."
            )

    def execute_tool(
        self,
        tool_name: str,
        tool_fn: Callable[..., Any],
        raw_args: Dict[str, Any],
        schema: Optional[Type[BaseModel]] = None,
    ) -> Dict[str, Any]:
        """Executes a tool safely with step limits, loop detection, and auto-healing validation."""
        start_time = time.perf_counter()
        self.current_steps += 1

        # 1. Step Circuit Breaker
        if self.current_steps > self.max_steps:
            raise BudgetExceededError(
                f"Max step limit reached ({self.max_steps}). Halting agent execution."
            )

        # 2. Infinite Loop Detection
        call_hash = self._hash_call(tool_name, raw_args)
        self._call_counts[call_hash] = self._call_counts.get(call_hash, 0) + 1
        if self._call_counts[call_hash] > self.max_duplicate_calls:
            raise InfiniteLoopDetected(
                f"Loop detected: '{tool_name}' called {self._call_counts[call_hash]} times "
                f"with identical arguments. Try a different approach."
            )

        # 3. Auto-Healing Schema Validation
        validated_args = raw_args
        if schema is not None:
            try:
                validated_obj = schema(**raw_args)
                validated_args = validated_obj.model_dump()
            except ValidationError as exc:
                latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
                error_feedback = (
                    f"Tool argument validation failed for '{tool_name}'. "
                    f"Fix these errors and retry: {exc.errors()}"
                )
                self._log_event(tool_name, raw_args, "validation_error", latency_ms, error_feedback)
                return {"status": "error", "recoverable": True, "message": error_feedback}

        # 4. Execute Tool Safely
        try:
            result = tool_fn(**validated_args)
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._log_event(tool_name, validated_args, "success", latency_ms, result)
            return {"status": "success", "output": result}
        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._log_event(tool_name, validated_args, "tool_runtime_error", latency_ms, str(exc))
            return {"status": "error", "recoverable": True, "message": f"Tool execution error: {exc}"}

    def _log_event(
        self, tool: str, args: Dict[str, Any], status: str, latency_ms: float, output: Any
    ) -> None:
        self.trace_logs.append(
            {
                "step": self.current_steps,
                "tool": tool,
                "args": args,
                "status": status,
                "latency_ms": latency_ms,
                "output_preview": str(output)[:200],
            }
        )

    def export_trace(self) -> str:
        return json.dumps(self.trace_logs, indent=2)
