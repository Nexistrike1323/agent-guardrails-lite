class GuardrailException(Exception):
    """Base exception for agent guardrail violations."""


class InfiniteLoopDetected(GuardrailException):
    """Raised when an agent repeats the exact same tool call beyond the allowed threshold."""


class BudgetExceededError(GuardrailException):
    """Raised when maximum steps or token limits are exceeded."""
