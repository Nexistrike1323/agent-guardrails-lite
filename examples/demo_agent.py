from pydantic import BaseModel, Field
from agent_guardrails import (
    BudgetExceededError,
    GuardrailSession,
    InfiniteLoopDetected,
)


class FileReadArgs(BaseModel):
    filepath: str = Field(..., pattern=r"^[\w\-./]+$")


def read_log_file(filepath: str) -> str:
    return f"[INFO] Loaded log file: {filepath} (0 critical errors)"


def run_demo():
    session = GuardrailSession(max_steps=6, max_tokens=8000, max_duplicate_calls=2)
    print("=== Starting Protected Agent Simulation ===\n")

    print("Turn 1: Calling tool with invalid path characters...")
    res1 = session.execute_tool("read_log", read_log_file, {"filepath": "bad path!!"}, schema=FileReadArgs)
    print(f"Response: {res1}\n")

    print("Turn 2: Agent self-corrects argument...")
    res2 = session.execute_tool("read_log", read_log_file, {"filepath": "logs/build.log"}, schema=FileReadArgs)
    print(f"Response: {res2}\n")

    try:
        print("Turn 3: Repeating identical call...")
        session.execute_tool("read_log", read_log_file, {"filepath": "logs/build.log"}, schema=FileReadArgs)
        print("Turn 4: Repeating identical call a 3rd time...")
        session.execute_tool("read_log", read_log_file, {"filepath": "logs/build.log"}, schema=FileReadArgs)
    except InfiniteLoopDetected as exc:
        print(f"[GUARDRAIL INTERCEPTED]: {exc}\n")

    print("=== Structured Execution Trace ===")
    print(session.export_trace())


if __name__ == "__main__":
    run_demo()
